"""
PDF processing utilities and classes.
"""

import io
import os
import re
from typing import Dict, List, Optional

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    fitz = None
    PYMUPDF_AVAILABLE = False

try:
    import pypdf

    PYPDF_AVAILABLE = True
except ImportError:
    pypdf = None
    PYPDF_AVAILABLE = False

from shared.utils.logging import logger


class PDFProcessor:
    """PDF processing utility class."""

    @staticmethod
    def is_pdf_library_available() -> bool:
        """Check if any PDF library is available."""
        return PYMUPDF_AVAILABLE or PYPDF_AVAILABLE

    @staticmethod
    def get_available_library() -> str:
        """Get the name of available PDF library."""
        if PYMUPDF_AVAILABLE:
            return "PyMuPDF"
        elif PYPDF_AVAILABLE:
            return "pypdf"
        return "None"

    @staticmethod
    def parse_page_range(page_range: Optional[str], total_pages: int) -> List[int]:
        """Parse page range string into list of page numbers."""
        if not page_range:
            return list(range(1, total_pages + 1))

        pages = []
        for part in page_range.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = map(int, part.split("-", 1))
                    pages.extend(range(start, min(end + 1, total_pages + 1)))
                except ValueError:
                    logger.warning(f"Invalid page range part: {part}")
                    continue
            else:
                try:
                    page_num = int(part)
                    if 1 <= page_num <= total_pages:
                        pages.append(page_num)
                except ValueError:
                    logger.warning(f"Invalid page number: {part}")
                    continue

        return sorted(list(set(pages)))

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize extracted text for better processing."""
        if not text:
            return ""

        # Remove excessive whitespace and normalize line breaks
        # Multiple empty lines to double
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)  # Multiple spaces to single
        text = re.sub(r"\t+", " ", text)  # Tabs to spaces

        # Fix common OCR/extraction issues
        text = text.replace("\x00", "")  # Remove null characters
        text = text.replace("\ufeff", "")  # Remove BOM
        # Remove control characters
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)

        # Normalize unicode quotation marks and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(""", "'").replace(""", "'")
        text = text.replace("–", "-").replace("—", "-")

        return text.strip()

    @staticmethod
    def extract_with_pymupdf(
        file_path: str, page_range: Optional[str] = None, enhanced_extraction: bool = True
    ) -> Dict:
        """Extract text using PyMuPDF with enhanced options."""
        if not PYMUPDF_AVAILABLE or fitz is None:
            raise ImportError("PyMuPDF not available")

        doc = fitz.open(file_path)  # type: ignore
        total_pages = doc.page_count

        pages_to_extract = PDFProcessor.parse_page_range(page_range, total_pages)

        pages_content = []
        full_text = []

        for page_num in pages_to_extract:
            page = doc[page_num - 1]  # PyMuPDF uses 0-based indexing

            if enhanced_extraction:
                # Use multiple extraction methods for better quality
                try:
                    # Method 1: Standard text extraction
                    text1 = getattr(page, "get_text", lambda: "")()

                    # Method 2: Extract with layout preservation
                    text2 = getattr(page, "get_text", lambda layout="layout": "")(layout="layout")

                    # Method 3: Extract text blocks with position info
                    blocks = getattr(page, "get_text", lambda output="dict": {})("dict")
                    text3 = ""
                    if isinstance(blocks, dict) and "blocks" in blocks:
                        for block in blocks["blocks"]:
                            if "lines" in block:
                                for line in block["lines"]:
                                    line_text = ""
                                    if "spans" in line:
                                        for span in line["spans"]:
                                            if "text" in span:
                                                line_text += span["text"]
                                    if line_text.strip():
                                        text3 += line_text + "\n"

                    # Choose the best extraction result
                    texts = [text1, text2, text3]
                    # Select the text with most content and reasonable
                    # formatting
                    text = max(texts, key=lambda t: len(t.strip()) if t else 0)

                except Exception as e:
                    logger.warning(f"Enhanced extraction failed for page {page_num}: {e}")
                    text = getattr(page, "get_text", lambda: "")()
            else:
                text = getattr(page, "get_text", lambda: "")()

            # Clean the extracted text
            cleaned_text = PDFProcessor.clean_text(text)

            pages_content.append(
                {
                    "page": page_num,
                    "content": cleaned_text,
                    "raw_content": text,  # Keep original for debugging
                    "word_count": len(cleaned_text.split()),
                    "char_count": len(cleaned_text),
                }
            )
            full_text.append(cleaned_text)

        doc.close()

        combined_text = "\n\n".join(full_text)

        return {
            "content": combined_text,
            "pages": pages_content,
            "total_pages": total_pages,
            "extracted_pages": len(pages_to_extract),
            "word_count": len(combined_text.split()),
            "char_count": len(combined_text),
            "library_used": "PyMuPDF",
            "enhanced_extraction": enhanced_extraction,
        }

    @staticmethod
    def extract_with_pypdf(
        file_path: str, page_range: Optional[str] = None, enhanced_extraction: bool = True
    ) -> Dict:
        """Extract text using pypdf with enhanced options."""
        if not PYPDF_AVAILABLE or pypdf is None:
            raise ImportError("pypdf not available")

        with open(file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            total_pages = len(pdf_reader.pages)

            pages_to_extract = PDFProcessor.parse_page_range(page_range, total_pages)

            pages_content = []
            full_text = []

            for page_num in pages_to_extract:
                # pypdf uses 0-based indexing
                page = pdf_reader.pages[page_num - 1]

                if enhanced_extraction:
                    try:
                        # Extract text with different methods
                        text1 = page.extract_text()

                        # Try with different extraction parameters if available
                        text2 = ""
                        if hasattr(page, "extract_text"):
                            try:
                                # Some versions support space_width parameter
                                text2 = page.extract_text(space_width=200)
                            except TypeError:
                                text2 = page.extract_text()

                        # Choose better result
                        text = text1 if len(text1) >= len(text2) else text2

                    except Exception as e:
                        logger.warning(f"Enhanced extraction failed for page {page_num}: {e}")
                        text = page.extract_text()
                else:
                    text = page.extract_text()

                # Clean the extracted text
                cleaned_text = PDFProcessor.clean_text(text)

                pages_content.append(
                    {
                        "page": page_num,
                        "content": cleaned_text,
                        "raw_content": text,
                        "word_count": len(cleaned_text.split()),
                        "char_count": len(cleaned_text),
                    }
                )
                full_text.append(cleaned_text)

            combined_text = "\n\n".join(full_text)

            return {
                "content": combined_text,
                "pages": pages_content,
                "total_pages": total_pages,
                "extracted_pages": len(pages_to_extract),
                "word_count": len(combined_text.split()),
                "char_count": len(combined_text),
                "library_used": "pypdf",
                "enhanced_extraction": enhanced_extraction,
            }

    @staticmethod
    def search_text_in_pdf(
        file_path: str,
        search_term: str,
        case_sensitive: bool = False,
        page_range: Optional[str] = None,
    ) -> Dict:
        """Search for specific text within a PDF file."""
        try:
            # Extract text first
            if PDFProcessor.get_available_library() == "PyMuPDF":
                extraction_result = PDFProcessor.extract_with_pymupdf(file_path, page_range)
            else:
                extraction_result = PDFProcessor.extract_with_pypdf(file_path, page_range)

            if not extraction_result.get("content"):
                return {"error": "No text content found in PDF"}

            # Search logic
            search_term_normalized = search_term if case_sensitive else search_term.lower()
            matches = []

            for page_info in extraction_result["pages"]:
                page_content = page_info["content"]
                page_content_normalized = page_content if case_sensitive else page_content.lower()

                # Find all occurrences
                start = 0
                while True:
                    pos = page_content_normalized.find(search_term_normalized, start)
                    if pos == -1:
                        break

                    # Extract context around the match
                    context_start = max(0, pos - 100)
                    context_end = min(len(page_content), pos + len(search_term) + 100)
                    context = page_content[context_start:context_end]

                    matches.append(
                        {
                            "page": page_info["page"],
                            "position": pos,
                            "context": context,
                            "match": page_content[pos : pos + len(search_term)],
                        }
                    )

                    start = pos + 1

            return {
                "success": True,
                "search_term": search_term,
                "case_sensitive": case_sensitive,
                "total_matches": len(matches),
                "matches": matches,
                "pages_searched": len(extraction_result["pages"]),
                "total_pages": extraction_result["total_pages"],
            }

        except Exception as e:
            logger.error(f"Error searching text in PDF: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_metadata_pymupdf(file_path: str) -> Dict:
        """Get metadata using PyMuPDF."""
        if not PYMUPDF_AVAILABLE or fitz is None:
            raise ImportError("PyMuPDF not available")

        doc = fitz.open(file_path)  # type: ignore
        metadata = doc.metadata

        # Handle case where metadata might be None
        if metadata is None:
            metadata = {}

        result = {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": doc.page_count,
            "file_size": os.path.getsize(file_path),
            "library_used": "PyMuPDF",
        }

        doc.close()
        return result

    @staticmethod
    def get_metadata_pypdf(file_path: str) -> Dict:
        """Get metadata using pypdf."""
        if not PYPDF_AVAILABLE or pypdf is None:
            raise ImportError("pypdf not available")

        with open(file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            metadata = pdf_reader.metadata

            # Handle case where metadata might be None
            if metadata is None:
                metadata = {}

            return {
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": str(metadata.get("/CreationDate", "")),
                "modification_date": str(metadata.get("/ModDate", "")),
                "page_count": len(pdf_reader.pages),
                "file_size": os.path.getsize(file_path),
                "library_used": "pypdf",
            }

    @staticmethod
    def get_page_count_pymupdf(file_path: str) -> int:
        """Get page count using PyMuPDF."""
        if not PYMUPDF_AVAILABLE or fitz is None:
            raise ImportError("PyMuPDF not available")

        doc = fitz.open(file_path)  # type: ignore
        page_count = doc.page_count
        doc.close()
        return page_count

    @staticmethod
    def get_page_count_pypdf(file_path: str) -> int:
        """Get page count using pypdf."""
        if not PYPDF_AVAILABLE or pypdf is None:
            raise ImportError("pypdf not available")

        with open(file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            return len(pdf_reader.pages)

    @staticmethod
    def extract_from_bytes_pymupdf(pdf_bytes: bytes, page_range: Optional[str] = None) -> Dict:
        """Extract text from PDF bytes using PyMuPDF."""
        if not PYMUPDF_AVAILABLE or fitz is None:
            raise ImportError("PyMuPDF not available")

        # Create a file-like object from bytes
        pdf_stream = io.BytesIO(pdf_bytes)

        doc = fitz.open(stream=pdf_stream, filetype="pdf")  # type: ignore
        total_pages = doc.page_count

        pages_to_extract = PDFProcessor.parse_page_range(page_range, total_pages)

        pages_content = []
        full_text = []

        for page_num in pages_to_extract:
            page = doc[page_num - 1]  # PyMuPDF uses 0-based indexing
            text = getattr(page, "get_text", lambda: "")()

            pages_content.append(
                {"page": page_num, "content": text, "word_count": len(text.split())}
            )
            full_text.append(text)

        doc.close()
        pdf_stream.close()

        combined_text = "\n\n".join(full_text)

        return {
            "content": combined_text,
            "pages": pages_content,
            "total_pages": total_pages,
            "extracted_pages": len(pages_to_extract),
            "word_count": len(combined_text.split()),
            "char_count": len(combined_text),
            "library_used": "PyMuPDF",
        }

    @staticmethod
    def extract_from_bytes_pypdf(pdf_bytes: bytes, page_range: Optional[str] = None) -> Dict:
        """Extract text from PDF bytes using pypdf."""
        if not PYPDF_AVAILABLE or pypdf is None:
            raise ImportError("pypdf not available")

        # Create a file-like object from bytes
        pdf_stream = io.BytesIO(pdf_bytes)

        pdf_reader = pypdf.PdfReader(pdf_stream)
        total_pages = len(pdf_reader.pages)

        pages_to_extract = PDFProcessor.parse_page_range(page_range, total_pages)

        pages_content = []
        full_text = []

        for page_num in pages_to_extract:
            # pypdf uses 0-based indexing
            page = pdf_reader.pages[page_num - 1]
            text = page.extract_text()

            pages_content.append(
                {"page": page_num, "content": text, "word_count": len(text.split())}
            )
            full_text.append(text)

        pdf_stream.close()

        combined_text = "\n\n".join(full_text)

        return {
            "content": combined_text,
            "pages": pages_content,
            "total_pages": total_pages,
            "extracted_pages": len(pages_to_extract),
            "word_count": len(combined_text.split()),
            "char_count": len(combined_text),
            "library_used": "pypdf",
        }
