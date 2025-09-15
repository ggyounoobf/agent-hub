from fastapi import UploadFile
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import PyPDF2
import io
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# A tiny thread pool for CPU-bound PDF work so we don't block the event loop
_PDF_EXECUTOR = ThreadPoolExecutor(max_workers=4)


class PDFProcessor:
    """Handle PDF file processing for multi-agent queries."""

    # File size limits (reasonable for preventing abuse)
    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB for PDFs

    # Processing limits (feel free to tune)
    MAX_PAGES_PER_FILE = 100          # None = no limit, process all pages
    MAX_WORDS_PER_FILE = 25_000       # None = no limit
    MAX_TOTAL_WORDS = 50_000          # None = no limit
    MAX_CHARS_PER_PAGE = None         # None = unlimited per page

    # Context clamp to protect LLM token budget
    MAX_CONTEXT_CHARS = 60_000        # final assembled context cap (approx 15–25k tokens)

    # Optional performance limits (currently unused but available)
    DEFAULT_MAX_PAGES = 1000
    DEFAULT_MAX_WORDS = 200_000

    @classmethod
    async def process_pdfs(
        cls,
        files: List[UploadFile],
        db: AsyncSession = None,
        user_id: str = None,
        max_pages_per_file: Optional[int] = None,
        max_words_per_file: Optional[int] = None,
        max_total_words: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process uploaded PDF files with configurable limits.
        """
        if not files:
            return {"files": [], "content": "", "summary": "No PDFs uploaded"}

        # Use provided limits or class defaults
        pages_limit = max_pages_per_file if max_pages_per_file is not None else cls.MAX_PAGES_PER_FILE
        words_per_file_limit = max_words_per_file if max_words_per_file is not None else cls.MAX_WORDS_PER_FILE
        total_words_limit = max_total_words if max_total_words is not None else cls.MAX_TOTAL_WORDS

        logger.info("📊 PDF Processing Limits:")
        logger.info(f"  📄 Pages per file: {pages_limit or 'unlimited'}")
        logger.info(f"  📝 Words per file: {words_per_file_limit or 'unlimited'}")
        logger.info(f"  📋 Total words: {total_words_limit or 'unlimited'}")

        processed_files: List[Dict[str, Any]] = []
        previews: List[str] = []
        total_words = 0

        for file in files:
            try:
                if not file.filename:
                    logger.warning("Skipping file with no filename")
                    continue

                if not file.filename.lower().endswith(".pdf"):
                    logger.warning(f"Skipping non-PDF file: {file.filename}")
                    processed_files.append({
                        "name": file.filename,
                        "error": "Not a PDF",
                        "processed": False
                    })
                    continue

                if total_words_limit and total_words >= total_words_limit:
                    logger.warning(f"Reached total word limit ({total_words_limit}). Skipping remaining files.")
                    processed_files.append({
                        "name": file.filename,
                        "error": "Skipped due to total word limit",
                        "processed": False
                    })
                    continue

                # Read the uploaded file once
                content = await file.read()
                size = len(content)
                if size > cls.MAX_FILE_SIZE:
                    raise ValueError(f"PDF too large: {size} bytes (max: {cls.MAX_FILE_SIZE})")

                remaining_budget = None
                if total_words_limit is not None:
                    remaining_budget = max(total_words_limit - total_words, 0)

                file_info = await cls._process_single_pdf_bytes(
                    name=file.filename,
                    data=content,
                    pages_limit=pages_limit,
                    words_limit=words_per_file_limit,
                    remaining_budget=remaining_budget,
                    per_page_char_limit=cls.MAX_CHARS_PER_PAGE,
                )

                if file_info and file_info.get("processed"):
                    processed_files.append(file_info)
                    previews.append(cls._create_content_preview(file_info))
                    total_words += file_info.get("word_count", 0)
                    
                    # Save PDF context to database if db and user_id are provided
                    if db and user_id and hasattr(file, 'file_id'):
                        from app.services.file_service import FileService
                        file_service = FileService()
                        await file_service.save_pdf_context(
                            db,
                            user_id,
                            file.file_id,
                            file_info.get("content", ""),
                            file_info.get("summary", "")
                        )
                elif file_info:
                    processed_files.append(file_info)

            except Exception as e:
                filename = file.filename or "unknown_file"
                logger.error(f"Error processing PDF {filename}: {e}")
                processed_files.append({
                    "name": filename,
                    "error": str(e),
                    "processed": False
                })

        # Create summary
        successful_files = [f for f in processed_files if f.get("processed", False)]
        summary = cls._create_summary(successful_files, total_words)

        # Clamp final context to avoid LLM token blow-ups
        context = "\n\n".join(previews)
        if cls.MAX_CONTEXT_CHARS is not None and len(context) > cls.MAX_CONTEXT_CHARS:
            logger.info(f"✂️ Clamping PDF context from {len(context)} to {cls.MAX_CONTEXT_CHARS} chars")
            context = context[:cls.MAX_CONTEXT_CHARS] + "\n\n[Content truncated due to context size limits]"

        return {
            "files": processed_files,
            "content": context,
            "summary": summary,
        }

    @classmethod
    async def _process_single_pdf_bytes(
        cls,
        name: str,
        data: bytes,
        pages_limit: Optional[int],
        words_limit: Optional[int],
        remaining_budget: Optional[int],
        per_page_char_limit: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """Process a single PDF (bytes) with optional constraints."""

        def _work() -> Dict[str, Any]:
            pdf_file = io.BytesIO(data)
            try:
                reader = PyPDF2.PdfReader(pdf_file)
            except Exception as e:
                raise ValueError(f"Failed to open PDF: {e}")

            is_encrypted = getattr(reader, "is_encrypted", False)
            if is_encrypted:
                # Attempt empty password (some PDFs are “encrypted” but openable)
                try:
                    reader.decrypt("")  # type: ignore[attr-defined]
                except Exception:
                    # Leave encrypted; we won't extract text
                    pass

            # If still encrypted after attempt, flag and stop
            if getattr(reader, "is_encrypted", False):
                return {
                    "name": name,
                    "size": len(data),
                    "type": "application/pdf",
                    "pages": 0,
                    "pages_processed": 0,
                    "content": "",
                    "processed": False,
                    "word_count": 0,
                    "truncated": False,
                    "is_encrypted": True,
                    "needs_ocr": False,
                    "error": "PDF is encrypted and requires a password",
                }

            num_pages = len(reader.pages)
            pages_to_process = num_pages
            if pages_limit is not None:
                pages_to_process = min(pages_to_process, pages_limit)

            extracted_chunks: List[str] = []
            current_word_count = 0
            pages_processed = 0
            any_text_found = False

            for page_idx in range(pages_to_process):
                try:
                    page = reader.pages[page_idx]
                    text = page.extract_text() or ""
                    text = text.strip()
                    if not text:
                        continue

                    any_text_found = True

                    # Honor per-page char limit (if set)
                    if per_page_char_limit is not None and len(text) > per_page_char_limit:
                        text = text[:per_page_char_limit] + "…"

                    page_words = len(text.split())

                    # Check file-level and total budgets
                    if words_limit is not None and current_word_count + page_words > words_limit:
                        break
                    if remaining_budget is not None and current_word_count + page_words > remaining_budget:
                        break

                    extracted_chunks.append(f"--- Page {page_idx + 1} ---\n{text}")
                    current_word_count += page_words
                    pages_processed += 1

                    if pages_processed % 50 == 0:
                        logger.info(f"📊 {name}: processed {pages_processed}/{pages_to_process} pages, {current_word_count} words")

                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_idx + 1} of {name}: {e}")
                    continue

            full_text = "\n\n".join(extracted_chunks)

            truncated = (
                pages_processed < num_pages or
                (words_limit is not None and current_word_count >= words_limit) or
                (remaining_budget is not None and current_word_count >= remaining_budget)
            )

            # If no text found, likely scanned/image-only → flag OCR need
            needs_ocr = not any_text_found and num_pages > 0

            return {
                "name": name,
                "size": len(data),
                "type": "application/pdf",
                "pages": num_pages,
                "pages_processed": pages_processed,
                "content": full_text,
                "processed": True,
                "word_count": current_word_count,
                "truncated": truncated,
                "is_encrypted": False,
                "needs_ocr": needs_ocr,
            }

        # Run the CPU-bound PDF parsing off the event loop
        return await asyncio.get_event_loop().run_in_executor(_PDF_EXECUTOR, _work)

    @classmethod
    def _create_content_preview(cls, file_info: Dict[str, Any]) -> str:
        """Create a structured content preview for the agent."""
        name = file_info["name"]
        pages = file_info.get("pages", 0)
        pages_processed = file_info.get("pages_processed", 0)
        word_count = file_info.get("word_count", 0)
        content = file_info.get("content", "")
        truncated = file_info.get("truncated", False)
        is_encrypted = file_info.get("is_encrypted", False)
        needs_ocr = file_info.get("needs_ocr", False)

        status_bits: List[str] = []
        if truncated:
            status_bits.append(f"⚠️ Partial {pages_processed}/{pages} pages, ~{word_count} words")
        elif pages_processed == pages and pages > 0:
            status_bits.append(f"✅ Complete {pages} pages, ~{word_count} words")
        if is_encrypted:
            status_bits.append("🔒 Encrypted")
        if needs_ocr:
            status_bits.append("🖼️ Likely scanned (needs OCR)")

        status_note = f" [{' | '.join(status_bits)}]" if status_bits else ""

        return f"""=== PDF: {name} ({pages} total pages){status_note} ===
Word Count: {word_count}
{content}"""

    @classmethod
    def _create_summary(cls, successful_files: List[Dict[str, Any]], total_words: int) -> str:
        """Create a summary of processed files."""
        if not successful_files:
            return "No PDFs successfully processed"

        total_pages = sum(f.get("pages", 0) for f in successful_files)
        total_processed_pages = sum(f.get("pages_processed", 0) for f in successful_files)
        complete_files = [f for f in successful_files if not f.get("truncated", False)]
        partial_files = [f for f in successful_files if f.get("truncated", False)]
        encrypted = sum(1 for f in successful_files if f.get("is_encrypted"))
        ocr_needed = sum(1 for f in successful_files if f.get("needs_ocr"))

        summary = f"Processed {len(successful_files)} PDF files ({total_processed_pages}/{total_pages} pages, ~{total_words} words)"
        if complete_files and partial_files:
            summary += f" [✅ {len(complete_files)} complete, ⚠️ {len(partial_files)} partial]"
        elif partial_files:
            summary += f" [⚠️ {len(partial_files)} partially processed]"
        elif complete_files:
            summary += f" [✅ All complete]"
        if encrypted:
            summary += f" [🔒 {encrypted} encrypted]"
        if ocr_needed:
            summary += f" [🖼️ {ocr_needed} may need OCR]"
        return summary

    @classmethod
    def create_pdf_context(cls, pdf_data: Dict[str, Any], user_prompt: str) -> str:
        """Create context string for the agent including PDF content."""
        content = pdf_data.get("content", "")
        if not content:
            return user_prompt

        pdf_summary = pdf_data.get("summary", "No PDFs")

        # Final safeguard: clamp again if caller bypassed process_pdfs
        if cls.MAX_CONTEXT_CHARS is not None and len(content) > cls.MAX_CONTEXT_CHARS:
            logger.info(f"✂️ Clamping provided PDF content in context to {cls.MAX_CONTEXT_CHARS} chars")
            content = content[:cls.MAX_CONTEXT_CHARS] + "\n\n[Content truncated due to context size limits]"

        context = f"""🔍 USER QUERY: {user_prompt}

📁 UPLOADED PDF DOCUMENT ANALYSIS:
{pdf_summary}

🧠 ANALYSIS INSTRUCTIONS:
- Use only the relevant excerpts from the content below; avoid quoting large blocks unless necessary.
- Reference page numbers when helpful.
- If information isn’t present in the PDFs, say so clearly.
- Summarize before expanding.

📄 EXTRACTED PDF CONTENT:
{content}

📋 TASK: Analyze the PDF content above and answer the user's query succinctly, then provide supporting details as needed."""
        return context
