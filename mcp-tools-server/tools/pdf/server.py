"""
PDF processing tools for the MCP Tools Server.
"""

import os
from typing import Dict, List, Optional

from shared.utils.logging import logger

from . import __version__
from .lightweight_rag import (
    CHROMADB_AVAILABLE,
    EMBEDDING_AVAILABLE,
    cleanup_pdf_index,
    get_pdf_index,
)
from .processors import PDFProcessor
from .utils import cleanup_temp_file, create_temp_pdf_file, get_pdf_summary, validate_pdf_file


def register_pdf_tools(mcp):
    """Register PDF processing tools with the MCP server."""

    @mcp.tool(name="pdf_extract_text", description="Extract text content from a PDF file.")
    def pdf_extract_text(file_path: str, page_range: Optional[str] = None) -> dict:
        """
        Extract text content from a PDF file.

        Args:
            file_path: Path to the PDF file
            page_range: Optional page range (e.g., "1-5" or "3,5,7")

        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            # Validate file
            validation = validate_pdf_file(file_path)
            if not validation["valid"]:
                return {"error": validation["error"]}

            # Check if PDF libraries are available
            if not PDFProcessor.is_pdf_library_available():
                return {"error": "No PDF library available. Install pypdf or PyMuPDF"}

            # Extract text using best available library
            try:
                if PDFProcessor.get_available_library() == "PyMuPDF":
                    result = PDFProcessor.extract_with_pymupdf(file_path, page_range)
                else:
                    result = PDFProcessor.extract_with_pypdf(file_path, page_range)

                # Add summary
                result["summary"] = get_pdf_summary(result["content"])
                return result

            except Exception as e:
                logger.error(f"Error extracting PDF text: {e}")
                return {"error": f"Failed to extract text: {str(e)}"}

        except Exception as e:
            logger.error(f"Error in pdf_extract_text: {e}")
            return {"error": str(e)}

    @mcp.tool(
        name="pdf_extract_from_bytes", description="Extract text content from PDF file bytes."
    )
    def pdf_extract_from_bytes(
        file_bytes: bytes, filename: str = "document.pdf", page_range: Optional[str] = None
    ) -> dict:
        """
        Extract text content from PDF file bytes.

        Args:
            file_bytes: PDF file content as bytes
            filename: Original filename for reference (default: "document.pdf")
            page_range: Optional page range (e.g., "1-5" or "3,5,7")

        Returns:
            Dictionary containing extracted text and metadata
        """
        temp_file_path = None
        try:
            # Create temporary file from bytes
            temp_file_path = create_temp_pdf_file(file_bytes)

            # Extract text using the file-based method
            result = pdf_extract_text(temp_file_path, page_range)

            # Update metadata to reflect original filename
            if "error" not in result:
                result["source_filename"] = filename
                result["source_type"] = "bytes"

            return result

        except Exception as e:
            logger.error(f"Error processing PDF bytes: {e}")
            return {"error": str(e)}
        finally:
            # Clean up temporary file
            if temp_file_path:
                cleanup_temp_file(temp_file_path)

    @mcp.tool(name="pdf_get_metadata", description="Get metadata information from a PDF file.")
    def pdf_get_metadata(file_path: str) -> dict:
        """
        Extract metadata from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing PDF metadata
        """
        try:
            # Validate file
            validation = validate_pdf_file(file_path)
            if not validation["valid"]:
                return {"error": validation["error"]}

            # Check if PDF libraries are available
            if not PDFProcessor.is_pdf_library_available():
                return {"error": "No PDF library available. Install pypdf or PyMuPDF"}

            # Get metadata using best available library
            try:
                if PDFProcessor.get_available_library() == "PyMuPDF":
                    result = PDFProcessor.get_metadata_pymupdf(file_path)
                else:
                    result = PDFProcessor.get_metadata_pypdf(file_path)

                return result

            except Exception as e:
                logger.error(f"Error extracting PDF metadata: {e}")
                return {"error": f"Failed to extract metadata: {str(e)}"}

        except Exception as e:
            logger.error(f"Error in pdf_get_metadata: {e}")
            return {"error": str(e)}

    @mcp.tool(name="pdf_search_text", description="Search for specific text within a PDF file.")
    def pdf_search_text(
        file_path: str, search_term: str, case_sensitive: bool = False, max_results: int = 10
    ) -> dict:
        """
        Search for specific text within a PDF file.

        Args:
            file_path: Path to the PDF file
            search_term: Text to search for
            case_sensitive: Whether search should be case sensitive (default: False)
            max_results: Maximum number of results to return (default: 10)

        Returns:
            Dictionary containing search results
        """
        try:
            # Validate file
            validation = validate_pdf_file(file_path)
            if not validation["valid"]:
                return {"error": validation["error"]}

            # Extract full text first
            extract_result = pdf_extract_text(file_path)
            if "error" in extract_result:
                return extract_result

            # Prepare search
            content = extract_result["content"]
            pages = extract_result.get("pages", [])

            if not case_sensitive:
                search_content = content.lower()
                search_term_normalized = search_term.lower()
            else:
                search_content = content
                search_term_normalized = search_term

            # Find all matches
            matches = []
            start = 0

            while len(matches) < max_results:
                pos = search_content.find(search_term_normalized, start)
                if pos == -1:
                    break

                # Extract context around the match
                context_start = max(0, pos - 100)
                context_end = min(len(content), pos + len(search_term) + 100)
                context = content[context_start:context_end]

                # Find which page this match is on
                page_num = 1
                chars_so_far = 0
                for page in pages:
                    page_content = page.get("content", "")
                    if chars_so_far + len(page_content) > pos:
                        page_num = page.get("page", 1)
                        break
                    chars_so_far += len(page_content) + 2  # +2 for \n\n separator

                matches.append(
                    {
                        "position": pos,
                        "page": page_num,
                        "context": context.strip(),
                        "match_text": content[pos : pos + len(search_term)],
                    }
                )

                start = pos + 1

            return {
                "search_term": search_term,
                "case_sensitive": case_sensitive,
                "total_matches": len(matches),
                "matches": matches,
                "file_info": {
                    "filename": os.path.basename(file_path),
                    "total_pages": extract_result.get("total_pages", 0),
                    "total_characters": len(content),
                },
            }

        except Exception as e:
            logger.error(f"Error searching PDF text: {e}")
            return {"error": str(e)}

    @mcp.tool(
        name="pdf_extract_pages", description="Extract text from specific pages of a PDF file."
    )
    def pdf_extract_pages(file_path: str, pages: List[int]) -> dict:
        """
        Extract text from specific pages of a PDF file.

        Args:
            file_path: Path to the PDF file
            pages: List of page numbers to extract (1-indexed)

        Returns:
            Dictionary containing extracted text from specified pages
        """
        try:
            # Validate file
            validation = validate_pdf_file(file_path)
            if not validation["valid"]:
                return {"error": validation["error"]}

            # Convert page list to page range string
            if not pages:
                return {"error": "No pages specified"}

            # Sort and validate page numbers
            pages = sorted(set(pages))
            if any(p < 1 for p in pages):
                return {"error": "Page numbers must be positive integers"}

            # Create page range string
            page_range = ",".join(str(p) for p in pages)

            # Extract using existing function
            result = pdf_extract_text(file_path, page_range)

            if "error" not in result:
                result["requested_pages"] = pages
                result["pages_found"] = len(result.get("pages", []))

            return result

        except Exception as e:
            logger.error(f"Error extracting PDF pages: {e}")
            return {"error": str(e)}

    @mcp.tool(name="pdf_get_page_count", description="Get the total number of pages in a PDF file.")
    def pdf_get_page_count(file_path: str) -> dict:
        """
        Get the total number of pages in a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing page count information
        """
        try:
            # Validate file
            validation = validate_pdf_file(file_path)
            if not validation["valid"]:
                return {"error": validation["error"]}

            # Check if PDF libraries are available
            if not PDFProcessor.is_pdf_library_available():
                return {"error": "No PDF library available. Install pypdf or PyMuPDF"}

            # Get page count using metadata extraction
            metadata_result = pdf_get_metadata(file_path)
            if "error" in metadata_result:
                return metadata_result

            return {
                "filename": os.path.basename(file_path),
                "page_count": metadata_result.get("page_count", 0),
                "file_size": metadata_result.get("file_size", 0),
                "library_used": metadata_result.get("library_used", "unknown"),
            }

        except Exception as e:
            logger.error(f"Error getting PDF page count: {e}")
            return {"error": str(e)}

    @mcp.tool(
        name="pdf_extract_text_with_coordinates",
        description="Extract text with positional coordinates (requires PyMuPDF).",
    )
    def pdf_extract_text_with_coordinates(file_path: str, page_number: int) -> dict:
        """
        Extract text with positional coordinates from a specific page.
        Requires PyMuPDF library.

        Args:
            file_path: Path to the PDF file
            page_number: Page number to extract (1-indexed)

        Returns:
            Dictionary containing text with coordinates
        """
        try:
            # Validate file
            validation = validate_pdf_file(file_path)
            if not validation["valid"]:
                return {"error": validation["error"]}

            # Check if PyMuPDF is available
            if PDFProcessor.get_available_library() != "PyMuPDF":
                return {"error": "This feature requires PyMuPDF. Install with: pip install PyMuPDF"}

            # Import here to avoid import errors if not available
            import fitz  # type: ignore

            doc = fitz.open(file_path)  # type: ignore
            total_pages = doc.page_count  # Store page count before we might close the doc

            if page_number < 1 or page_number > total_pages:
                doc.close()
                return {"error": f"Page {page_number} not found. Document has {total_pages} pages."}

            page = doc[page_number - 1]  # Convert to 0-indexed

            # Extract text with coordinates
            text_dict = page.get_text("dict")  # type: ignore

            # Process blocks and spans
            text_elements = []
            for block in text_dict["blocks"]:
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_elements.append(
                                {
                                    "text": span["text"],
                                    "bbox": span["bbox"],  # [x0, y0, x1, y1]
                                    "font": span["font"],
                                    "size": span["size"],
                                    "flags": span["flags"],
                                    "color": span["color"],
                                }
                            )

            doc.close()

            return {
                "page": page_number,
                "total_pages": total_pages,  # Use the stored value
                "text_elements": text_elements,
                "element_count": len(text_elements),
                "filename": os.path.basename(file_path),
            }

        except Exception as e:
            logger.error(f"Error extracting text with coordinates: {e}")
            return {"error": str(e)}

    @mcp.tool(
        name="pdf_process_multiple",
        description="Process multiple PDF files in batch for indexing and analysis.",
    )
    def pdf_process_multiple(
        file_paths: List[str], operations: List[str] = ["extract", "index"]
    ) -> dict:
        """
        Process multiple PDF files in batch.

        Args:
            file_paths: List of PDF file paths
            operations: List of operations to perform ("extract", "index", "metadata")

        Returns:
            Dictionary with batch processing results
        """
        try:
            results = []

            for file_path in file_paths:
                file_result = {"file_path": file_path, "operations": {}}

                try:
                    if "extract" in operations:
                        extract_result = pdf_extract_text(file_path)
                        file_result["operations"]["extract"] = extract_result

                    if "index" in operations and EMBEDDING_AVAILABLE:
                        index_result = pdf_index_document(file_path)
                        file_result["operations"]["index"] = index_result

                    if "metadata" in operations:
                        metadata_result = pdf_get_metadata(file_path)
                        file_result["operations"]["metadata"] = metadata_result

                except Exception as e:
                    file_result["error"] = str(e)

                results.append(file_result)

            return {
                "success": True,
                "processed_files": len(file_paths),
                "operations_performed": operations,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return {"error": str(e)}

    @mcp.tool(
        name="pdf_service_status", description="Check PDF service status and available libraries."
    )
    def pdf_service_status() -> dict:
        """
        Check PDF service status and show available libraries.

        Returns:
            Dictionary with service status information
        """
        try:
            # Check library availability
            pymupdf_available = False
            pypdf_available = False

            try:
                import fitz

                pymupdf_available = True
                pymupdf_version = fitz.version[0] if hasattr(fitz, "version") else "unknown"
            except ImportError:
                pymupdf_version = None

            try:
                import pypdf

                pypdf_available = True
                pypdf_version = getattr(pypdf, "__version__", "unknown")
            except ImportError:
                pypdf_version = None

            # Determine primary library
            primary_library = PDFProcessor.get_available_library()

            # Feature support
            features = {
                "text_extraction": pymupdf_available or pypdf_available,
                "metadata_extraction": pymupdf_available or pypdf_available,
                "page_range_support": True,
                "text_search": pymupdf_available or pypdf_available,
                "coordinate_extraction": pymupdf_available,
                "bytes_processing": True,
                "semantic_search": EMBEDDING_AVAILABLE,
                "vector_storage": CHROMADB_AVAILABLE,
            }

            # Update tool list to include RAG tools
            tools_list = [
                "pdf_extract_text",
                "pdf_extract_from_bytes",
                "pdf_get_metadata",
                "pdf_search_text",
                "pdf_extract_pages",
                "pdf_get_page_count",
                "pdf_extract_text_with_coordinates",
                "pdf_find_duplicates",
                "pdf_service_status",
                "pdf_process_multiple",
            ]

            # Add RAG tools if available
            if EMBEDDING_AVAILABLE:
                tools_list.extend(
                    [
                        "pdf_index_document",
                        "pdf_search_semantic",
                        "pdf_get_document_content",
                        "pdf_index_stats",
                        "pdf_clear_index",
                        "pdf_analyze_content_patterns",
                        "pdf_capabilities",
                    ]
                )

            return {
                "service_name": "PDF Processing Tools",
                "version": __version__,
                "status": "operational" if (pymupdf_available or pypdf_available) else "limited",
                "libraries": {
                    "PyMuPDF": {
                        "available": pymupdf_available,
                        "version": pymupdf_version,
                        "features": [
                            "text_extraction",
                            "metadata",
                            "coordinates",
                            "advanced_features",
                        ],
                    },
                    "pypdf": {
                        "available": pypdf_available,
                        "version": pypdf_version,
                        "features": ["text_extraction", "metadata", "basic_features"],
                    },
                    "sentence_transformers": {
                        "available": EMBEDDING_AVAILABLE,
                        "features": ["semantic_embeddings", "similarity_search"],
                    },
                    "chromadb": {
                        "available": CHROMADB_AVAILABLE,
                        "features": ["vector_storage", "semantic_search"],
                    },
                },
                "primary_library": primary_library,
                "features_available": features,
                "tools_registered": tools_list,
                "recommendations": _get_recommendations(pymupdf_available, pypdf_available),
            }

        except Exception as e:
            logger.error(f"Error checking PDF service status: {e}")
            return {"status": "error", "error": str(e), "version": __version__}

    def _get_recommendations(pymupdf_available: bool, pypdf_available: bool) -> List[str]:
        """Get recommendations for improving PDF processing capabilities."""
        recommendations = []

        if not pymupdf_available and not pypdf_available:
            recommendations.append(
                "Install a PDF library: pip install PyMuPDF or pip install pypdf"
            )
        elif not pymupdf_available:
            recommendations.append("Install PyMuPDF for advanced features: pip install PyMuPDF")
        elif not pypdf_available:
            recommendations.append("Consider pypdf as a lightweight alternative: pip install pypdf")

        if not EMBEDDING_AVAILABLE:
            recommendations.append(
                "Install sentence-transformers for semantic search: pip install sentence-transformers"
            )

        if not CHROMADB_AVAILABLE:
            recommendations.append("Install chromadb for vector storage: pip install chromadb")

        return recommendations

    # === LIGHTWEIGHT RETRIEVAL TOOLS (NO LLM CALLS) ===

    @mcp.tool(
        name="pdf_index_document",
        description="Index a PDF document for semantic search (no LLM calls).",
    )
    def pdf_index_document(file_path: str, metadata: Optional[Dict] = None) -> dict:
        """
        Index a PDF document for efficient retrieval and search.
        Pure indexing - no LLM calls made by the server.

        Args:
            file_path: Path to the PDF file
            metadata: Optional metadata for the document

        Returns:
            Dictionary with indexing results
        """
        pdf_index = get_pdf_index()
        if not pdf_index:
            return {"error": "Failed to initialize PDF index"}

        return pdf_index.add_pdf_document(file_path, metadata)

    @mcp.tool(
        name="pdf_search_semantic",
        description="Search indexed PDFs using semantic similarity (retrieval only).",
    )
    def pdf_search_semantic(query: str, top_k: int = 5, score_threshold: float = 0.1) -> dict:
        """
        Search indexed PDF documents using semantic similarity.
        Returns relevant content chunks for the client LLM to process.

        Args:
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            Dictionary with retrieved content chunks and sources
        """
        pdf_index = get_pdf_index()
        if not pdf_index:
            return {"error": "PDF index not initialized"}

        return pdf_index.search_similar_content(query, top_k, score_threshold)

    @mcp.tool(
        name="pdf_get_document_content",
        description="Get content summary of a specific indexed document.",
    )
    def pdf_get_document_content(document_id: str) -> dict:
        """
        Get content summary and metadata of a specific indexed document.

        Args:
            document_id: ID of the document to retrieve

        Returns:
            Dictionary with document content and metadata
        """
        pdf_index = get_pdf_index()
        if not pdf_index:
            return {"error": "PDF index not initialized"}

        return pdf_index.get_document_summary(document_id)

    @mcp.tool(name="pdf_index_stats", description="Get statistics about the PDF index.")
    def pdf_index_stats() -> dict:
        """
        Get comprehensive statistics about the PDF index.

        Returns:
            Dictionary with index statistics
        """
        pdf_index = get_pdf_index()
        if not pdf_index:
            return {"error": "PDF index not initialized"}

        return pdf_index.get_index_stats()

    @mcp.tool(name="pdf_clear_index", description="Clear all indexed PDF documents.")
    def pdf_clear_index() -> dict:
        """
        Clear all documents from the PDF index.

        Returns:
            Dictionary with operation result
        """
        pdf_index = get_pdf_index()
        if not pdf_index:
            return {"error": "PDF index not initialized"}

        return pdf_index.clear_index()

    @mcp.tool(
        name="pdf_analyze_content_patterns",
        description="Analyze content patterns and themes in PDF using semantic analysis.",
    )
    def pdf_analyze_content_patterns(
        file_path: str, pattern_query: str, top_k: int = 10, similarity_threshold: float = 0.7
    ) -> dict:
        """
        Analyze content patterns in PDF using RAG-based semantic search.

        Args:
            file_path: Path to the PDF file
            pattern_query: Query describing the pattern to search for
            top_k: Number of similar content pieces to return
            similarity_threshold: Minimum similarity score for results

        Returns:
            Dictionary with pattern analysis results
        """
        try:
            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}

            # Get the RAG index
            pdf_index = get_pdf_index()
            if pdf_index is None:
                return {"error": "RAG system not available"}

            # Index the document
            index_result = pdf_index.add_pdf_document(file_path)
            if not index_result.get("success"):
                return {"error": "Failed to index document"}

            # Search for the pattern
            search_result = pdf_index.search_similar_content(
                pattern_query, top_k=top_k, score_threshold=similarity_threshold
            )

            # Analyze the results
            content_pieces = search_result.get("retrieved_content", [])

            if not content_pieces:
                return {
                    "success": True,
                    "pattern_query": pattern_query,
                    "matches_found": 0,
                    "message": "No content matching the specified pattern was found",
                }

            # Group by similarity scores
            high_similarity = [c for c in content_pieces if c["score"] >= 0.9]
            medium_similarity = [c for c in content_pieces if 0.7 <= c["score"] < 0.9]
            low_similarity = [c for c in content_pieces if c["score"] < 0.7]

            return {
                "success": True,
                "pattern_query": pattern_query,
                "total_matches": len(content_pieces),
                "analysis": {
                    "high_similarity_matches": {
                        "count": len(high_similarity),
                        "content": high_similarity,
                    },
                    "medium_similarity_matches": {
                        "count": len(medium_similarity),
                        "content": medium_similarity,
                    },
                    "low_similarity_matches": {
                        "count": len(low_similarity),
                        "content": low_similarity,
                    },
                },
                "search_method": search_result.get("search_method", "unknown"),
                "source_documents": search_result.get("source_documents", []),
            }

        except Exception as e:
            logger.error(f"Error in content pattern analysis: {e}")
            return {"error": str(e)}

    @mcp.tool(
        name="pdf_capabilities", description="Check PDF processing and indexing capabilities."
    )
    def pdf_capabilities() -> dict:
        """
        Check available PDF processing and indexing capabilities.

        Returns:
            Dictionary with capability information
        """
        return {
            "basic_pdf_support": PDFProcessor.is_pdf_library_available(),
            "pdf_library": PDFProcessor.get_available_library(),
            "semantic_search": EMBEDDING_AVAILABLE,
            "vector_storage": CHROMADB_AVAILABLE,
            "features": [
                "Text extraction",
                "Metadata extraction",
                "Page-range processing",
                "Document indexing" if EMBEDDING_AVAILABLE else "Basic text search",
                "Semantic search" if EMBEDDING_AVAILABLE else "Keyword search",
                "Multi-document retrieval",
            ],
            "note": "This is a retrieval-only system. No LLM calls are made by the server.",
            "version": __version__,
        }

    @mcp.tool(
        name="pdf_find_duplicates",
        description="Find duplicate content within a PDF document using both traditional and semantic analysis.",
    )
    def pdf_find_duplicates(
        file_path: str,
        min_length: int = 10,
        similarity_threshold: float = 0.8,
        use_semantic_analysis: bool = True,
        semantic_similarity_threshold: float = 0.85,
    ) -> dict:
        """
        Find duplicate content in a PDF document using multiple detection methods.

        Args:
            file_path: Path to the PDF file
            min_length: Minimum length of content to consider for duplication
            similarity_threshold: Similarity threshold for traditional matching (0.0-1.0)
            use_semantic_analysis: Whether to use RAG for semantic duplicate detection
            semantic_similarity_threshold: Threshold for semantic similarity (0.0-1.0)

        Returns:
            Dictionary with comprehensive duplicate analysis results
        """
        try:
            # Validate file
            validation = validate_pdf_file(file_path)
            if not validation["valid"]:
                return {"error": validation["error"]}

            # Check if PDF libraries are available
            if not PDFProcessor.is_pdf_library_available():
                return {"error": "No PDF library available. Install pypdf or PyMuPDF"}

            # If semantic analysis requested but not available, fall back to
            # basic
            if use_semantic_analysis and not EMBEDDING_AVAILABLE:
                logger.warning(
                    "Semantic analysis requested but embeddings not available, using basic analysis only"
                )
                use_semantic_analysis = False

            # Extract text first
            extract_result = pdf_extract_text(file_path)
            if "error" in extract_result:
                return extract_result

            text = extract_result.get("content", "")
            if not text:
                return {"error": "No text content found in PDF"}

            # Basic duplicate detection
            basic_duplicates = _find_basic_duplicates(text, min_length, similarity_threshold)

            # Semantic duplicate detection if available and requested
            semantic_duplicates = []
            semantic_stats = {}

            if use_semantic_analysis and EMBEDDING_AVAILABLE:
                try:
                    pdf_index = get_pdf_index()
                    if pdf_index:
                        # Index the document
                        index_result = pdf_index.add_pdf_document(file_path)
                        if index_result.get("success"):
                            semantic_analysis = _find_semantic_duplicates_simple(
                                pdf_index, text, semantic_similarity_threshold
                            )
                            semantic_duplicates = semantic_analysis.get("duplicates", [])
                            semantic_stats = semantic_analysis.get("statistics", {})
                except Exception as e:
                    logger.warning(f"Semantic analysis failed: {e}")

            # Combine results
            all_duplicates = basic_duplicates.get("duplicates", []) + semantic_duplicates

            # Sort by importance
            all_duplicates.sort(
                key=lambda x: x.get("occurrences", 1) * x.get("length", 0), reverse=True
            )

            return {
                "success": True,
                "file_info": {
                    "file_path": file_path,
                    "total_pages": extract_result.get("total_pages", 0),
                    "word_count": extract_result.get("word_count", 0),
                    "char_count": len(text),
                },
                "analysis_results": {
                    "basic_duplicates": basic_duplicates.get("duplicates", [])[:20],
                    "semantic_duplicates": semantic_duplicates[:10] if semantic_duplicates else [],
                    "top_duplicates": all_duplicates[:15],
                },
                "statistics": {
                    "total_duplicate_patterns": len(all_duplicates),
                    "basic_stats": basic_duplicates.get("statistics", {}),
                    "semantic_stats": semantic_stats,
                },
                "analysis_parameters": {
                    "min_length": min_length,
                    "similarity_threshold": similarity_threshold,
                    "semantic_analysis_used": use_semantic_analysis,
                    "semantic_similarity_threshold": semantic_similarity_threshold,
                },
            }

        except Exception as e:
            logger.error(f"Error in duplicate detection: {e}")
            return {"error": str(e)}

    def _find_basic_duplicates(text: str, min_length: int, similarity_threshold: float) -> dict:
        """Find basic text duplicates using string matching."""
        import re
        from collections import Counter

        if not text:
            return {"duplicates": [], "statistics": {}}

        # Split into sentences and paragraphs
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) >= min_length]
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= min_length]

        duplicates = []

        # Find exact duplicates in sentences
        sentence_counts = Counter(sentences)
        for sentence, count in sentence_counts.items():
            if count > 1:
                duplicates.append(
                    {
                        "type": "exact_sentence",
                        "content": sentence,
                        "occurrences": count,
                        "length": len(sentence),
                        "similarity": 1.0,
                        "detection_method": "exact_match",
                    }
                )

        # Find exact duplicates in paragraphs
        paragraph_counts = Counter(paragraphs)
        for paragraph, count in paragraph_counts.items():
            if count > 1:
                duplicates.append(
                    {
                        "type": "exact_paragraph",
                        "content": paragraph,
                        "occurrences": count,
                        "length": len(paragraph),
                        "similarity": 1.0,
                        "detection_method": "exact_match",
                    }
                )

        # Calculate statistics
        total_chars = len(text)
        duplicate_chars = sum(d["length"] * (d["occurrences"] - 1) for d in duplicates)

        statistics = {
            "total_duplicates_found": len(duplicates),
            "total_characters": total_chars,
            "duplicate_characters": duplicate_chars,
            "duplication_percentage": (
                (duplicate_chars / total_chars * 100) if total_chars > 0 else 0
            ),
        }

        return {"duplicates": duplicates, "statistics": statistics}

    def _find_semantic_duplicates_simple(pdf_index, text: str, threshold: float) -> dict:
        """Find semantic duplicates using the RAG index."""
        try:
            # Split text into chunks
            chunks = _create_analysis_chunks(text)

            semantic_duplicates = []
            processed_chunks = set()

            for i, chunk in enumerate(chunks):
                if i in processed_chunks:
                    continue

                # Search for similar content
                search_result = pdf_index.search_similar_content(
                    chunk, top_k=10, score_threshold=threshold
                )

                similar_chunks = []
                for result in search_result.get("retrieved_content", []):
                    if result["score"] >= threshold and result["content"] != chunk:
                        similar_chunks.append(
                            {"content": result["content"], "score": result["score"]}
                        )

                if similar_chunks:
                    processed_chunks.add(i)
                    semantic_duplicates.append(
                        {
                            "type": "semantic_duplicate",
                            "primary_content": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                            "similar_content_count": len(similar_chunks),
                            "avg_similarity": sum(sc["score"] for sc in similar_chunks)
                            / len(similar_chunks),
                            "occurrences": len(similar_chunks) + 1,
                            "length": len(chunk),
                            "detection_method": "semantic_embedding",
                        }
                    )

            statistics = {
                "semantic_duplicate_groups": len(semantic_duplicates),
                "method": "semantic_embedding_analysis",
            }

            return {"duplicates": semantic_duplicates, "statistics": statistics}

        except Exception as e:
            logger.error(f"Semantic duplicate detection failed: {e}")
            return {"duplicates": [], "statistics": {"error": str(e)}}

    def _create_analysis_chunks(text: str, chunk_size: int = 500) -> List[str]:
        """Create chunks for semantic analysis."""
        import re

        sentences = [s.strip() + "." for s in re.split(r"[.!?]+", text) if len(s.strip()) > 20]

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    logger.debug("PDF processing tools (with lightweight retrieval) registered")


async def cleanup_pdf_service():
    """Cleanup PDF service resources."""
    try:
        cleanup_pdf_index()
        logger.info("✅ PDF service cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up PDF service: {e}")
