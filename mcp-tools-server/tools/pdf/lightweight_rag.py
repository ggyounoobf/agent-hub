"""
Lightweight RAG processor for PDF documents - retrieval only, no LLM calls.
Focuses on semantic search and document indexing for the MCP client LLM to use.
"""

import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from shared.utils.logging import logger

from .processors import PDFProcessor

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import faiss  # type: ignore

    FAISS_AVAILABLE = True
    # Test FAISS functionality
    try:
        # Try to create a simple index to verify FAISS works
        test_index = faiss.IndexFlatL2(128)
        FAISS_FUNCTIONAL = True
    except Exception as e:
        print(f"FAISS available but not functional: {e}")
        FAISS_FUNCTIONAL = False
except ImportError:
    faiss = None
    FAISS_AVAILABLE = False
    FAISS_FUNCTIONAL = False

# Combined embedding availability
EMBEDDING_AVAILABLE = SENTENCE_TRANSFORMERS_AVAILABLE and FAISS_FUNCTIONAL

try:
    import chromadb  # type: ignore
    from chromadb.utils import embedding_functions  # type: ignore

    CHROMADB_AVAILABLE = True
    # Test ChromaDB functionality
    try:
        test_client = chromadb.EphemeralClient()
        CHROMADB_FUNCTIONAL = True
    except Exception as e:
        print(f"ChromaDB available but not functional: {e}")
        CHROMADB_FUNCTIONAL = False
except ImportError:
    chromadb = None
    embedding_functions = None
    CHROMADB_AVAILABLE = False
    CHROMADB_FUNCTIONAL = False


class LightweightPDFIndex:
    """Lightweight PDF indexing system without LLM calls - retrieval only."""

    def __init__(self, collection_name: str = "pdf_documents", use_chromadb: bool = True):
        """Initialize the lightweight index."""
        self.collection_name = collection_name
        self.use_chromadb = use_chromadb

        # Document storage
        self.documents: Dict[str, Dict] = {}  # doc_id -> document data
        self.chunks: Dict[str, Dict] = {}  # chunk_id -> chunk data

        # Embedding components
        self.embedding_model: Optional[Any] = None
        self.embedding_dim: Optional[int] = None

        # Vector storage
        self.chroma_client: Optional[Any] = None
        self.chroma_collection: Optional[Any] = None
        self.faiss_index: Optional[Any] = None
        self.chunk_ids: List[str] = []  # For FAISS index mapping

        self._setup_embeddings()
        self._setup_vector_store()

    def _setup_embeddings(self):
        """Setup embedding model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE or SentenceTransformer is None:
            logger.warning("SentenceTransformers not available - using basic text search only")
            return

        try:
            self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            logger.info("✅ Embedding model loaded (no LLM calls)")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embedding_model = None

    def _setup_vector_store(self):
        """Setup vector storage (ChromaDB or FAISS)."""
        # Try ChromaDB first if available and requested
        if (
            self.use_chromadb
            and CHROMADB_AVAILABLE
            and CHROMADB_FUNCTIONAL
            and chromadb is not None
            and embedding_functions is not None
            and self.embedding_model is not None
        ):
            try:
                self.chroma_client = chromadb.EphemeralClient()

                # Use sentence transformers embedding function
                sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )

                self.chroma_collection = self.chroma_client.create_collection(
                    name=self.collection_name, embedding_function=sentence_transformer_ef
                )
                logger.info("✅ ChromaDB vector store ready")
                return
            except Exception as e:
                logger.error(f"ChromaDB setup failed: {e}")
                # Fall through to FAISS

        # Try FAISS as fallback
        self._setup_faiss_fallback()

    def _setup_faiss_fallback(self):
        """Setup FAISS as fallback vector store."""
        if not (
            self.embedding_model and self.embedding_dim and FAISS_AVAILABLE and FAISS_FUNCTIONAL
        ):
            logger.warning(
                "FAISS not available or embedding model not loaded - using text search only"
            )
            return

        try:
            if faiss is None:
                logger.warning("FAISS module not available")
                return

            # Use CPU-only FAISS with cosine similarity
            # IndexFlatIP is for inner product (cosine similarity when vectors
            # are normalized)
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
            logger.info("✅ FAISS vector store ready (CPU)")

        except Exception as e:
            logger.warning(f"FAISS setup failed: {e} - using text search only")
            self.faiss_index = None

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence end
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if text[i] in ".!?":
                        end = i + 1
                        break
                else:
                    # Look for word boundary
                    for i in range(end, max(start + chunk_size - 50, start), -1):
                        if text[i] == " ":
                            end = i
                            break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    def add_pdf_document(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Add a PDF document to the index (retrieval preparation only).

        Args:
            file_path: Path to the PDF file
            metadata: Optional metadata for the document

        Returns:
            Dictionary with indexing results
        """
        try:
            # Extract text using existing processor
            if PDFProcessor.get_available_library() == "PyMuPDF":
                pdf_data = PDFProcessor.extract_with_pymupdf(file_path)
            else:
                pdf_data = PDFProcessor.extract_with_pypdf(file_path)

            if not pdf_data.get("content"):
                return {"error": "No text content extracted from PDF"}

            document_id = str(uuid.uuid4())

            # Store document metadata
            doc_metadata = {
                "document_id": document_id,
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "total_pages": pdf_data.get("total_pages", 0),
                "word_count": pdf_data.get("word_count", 0),
                "indexed_at": datetime.now().isoformat(),
            }

            if metadata:
                doc_metadata.update(metadata)

            self.documents[document_id] = {
                "metadata": doc_metadata,
                "full_text": pdf_data["content"],
                "pages": pdf_data.get("pages", []),
            }

            # Chunk the document
            chunks = self._chunk_text(pdf_data["content"])
            chunk_count = 0

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"

                chunk_data = {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "chunk_index": i,
                    "text": chunk,
                    "word_count": len(chunk.split()),
                    "char_count": len(chunk),
                    "metadata": doc_metadata.copy(),
                }

                self.chunks[chunk_id] = chunk_data

                # Add to vector store if available
                if self._add_chunk_to_vector_store(chunk_id, chunk, doc_metadata):
                    chunk_count += 1

            # Determine indexing method used
            indexing_method = "text_only"
            if self.chroma_collection is not None:
                indexing_method = "chromadb"
            elif self.faiss_index is not None:
                indexing_method = "faiss"

            return {
                "success": True,
                "document_id": document_id,
                "pages_processed": pdf_data.get("total_pages", 0),
                "chunks_created": len(chunks),
                "chunks_indexed": chunk_count,
                "word_count": pdf_data.get("word_count", 0),
                "indexing_method": indexing_method,
                "message": f"Successfully indexed {os.path.basename(file_path)} for retrieval",
            }

        except Exception as e:
            logger.error(f"Error indexing PDF: {e}")
            return {"error": str(e)}

    def add_pdf_from_bytes(
        self, file_bytes: bytes, filename: str, metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Add a PDF from bytes to the index.

        Args:
            file_bytes: PDF file content as bytes
            filename: Original filename
            metadata: Optional metadata for the document

        Returns:
            Dictionary with indexing results
        """
        temp_file_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(file_bytes)
                temp_file_path = tmp_file.name

            # Add metadata about source
            if metadata is None:
                metadata = {}
            metadata["source_type"] = "bytes"
            metadata["original_filename"] = filename

            result = self.add_pdf_document(temp_file_path, metadata)

            return result

        except Exception as e:
            logger.error(f"Error processing PDF bytes: {e}")
            return {"error": str(e)}
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

    def _add_chunk_to_vector_store(self, chunk_id: str, text: str, metadata: Dict) -> bool:
        """Add chunk to vector store."""
        try:
            if self.chroma_collection is not None:
                # Add to ChromaDB
                self.chroma_collection.add(ids=[chunk_id], documents=[text], metadatas=[metadata])
                return True

            elif self.faiss_index is not None and self.embedding_model is not None:
                # Add to FAISS
                embedding = self.embedding_model.encode([text])
                # Normalize for cosine similarity
                embedding = embedding / np.linalg.norm(embedding, axis=1, keepdims=True)
                self.faiss_index.add(embedding.astype("float32"))
                self.chunk_ids.append(chunk_id)
                return True

        except Exception as e:
            logger.error(f"Error adding chunk to vector store: {e}")

        return False

    def search_similar_content(
        self, query: str, top_k: int = 5, score_threshold: float = 0.1
    ) -> Dict:
        """
        Search for similar content (pure retrieval - no LLM calls).

        Args:
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            Dictionary with search results and retrieved content
        """
        try:
            results = []
            search_method = "text_based"

            if self.chroma_collection is not None:
                # ChromaDB search
                search_method = "chromadb_semantic"
                chroma_results = self.chroma_collection.query(query_texts=[query], n_results=top_k)

                for i, (chunk_id, distance, document, metadata) in enumerate(
                    zip(
                        chroma_results["ids"][0],
                        chroma_results["distances"][0],
                        chroma_results["documents"][0],
                        chroma_results["metadatas"][0],
                    )
                ):
                    similarity = 1 - distance  # Convert distance to similarity
                    if similarity >= score_threshold:
                        results.append(
                            {
                                "chunk_id": chunk_id,
                                "similarity_score": similarity,
                                "text": document,
                                "metadata": metadata,
                                "rank": i + 1,
                            }
                        )

            elif self.faiss_index is not None and self.embedding_model is not None:
                # FAISS search
                search_method = "faiss_semantic"
                query_embedding = self.embedding_model.encode([query])
                query_embedding = query_embedding / np.linalg.norm(
                    query_embedding, axis=1, keepdims=True
                )

                scores, indices = self.faiss_index.search(query_embedding.astype("float32"), top_k)

                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if idx >= 0 and idx < len(self.chunk_ids) and score >= score_threshold:
                        chunk_id = self.chunk_ids[idx]
                        chunk_data = self.chunks.get(chunk_id, {})

                        results.append(
                            {
                                "chunk_id": chunk_id,
                                "similarity_score": float(score),
                                "text": chunk_data.get("text", ""),
                                "metadata": chunk_data.get("metadata", {}),
                                "rank": i + 1,
                            }
                        )

            else:
                # Fallback: basic text search
                return self._basic_text_search(query, top_k)

            # Prepare retrieved content for the client LLM
            retrieved_content = []
            source_documents = set()

            for result in results:
                retrieved_content.append(
                    {
                        "content": result["text"],
                        "source": result["metadata"].get("file_name", "unknown"),
                        "score": result["similarity_score"],
                        "document_id": result["metadata"].get("document_id", "unknown"),
                    }
                )
                source_documents.add(result["metadata"].get("file_name", "unknown"))

            return {
                "query": query,
                "total_results": len(results),
                "retrieved_content": retrieved_content,
                "source_documents": list(source_documents),
                "search_method": search_method,
            }

        except Exception as e:
            logger.error(f"Error searching content: {e}")
            return {"error": str(e)}

    def _basic_text_search(self, query: str, top_k: int) -> Dict:
        """Fallback basic text search when embeddings aren't available."""
        query_lower = query.lower()
        results = []

        for chunk_id, chunk_data in self.chunks.items():
            text = chunk_data["text"].lower()

            # Simple scoring: count query word matches
            query_words = query_lower.split()
            if query_words:
                score = sum(1 for word in query_words if word in text) / len(query_words)

                if score > 0:
                    results.append(
                        {
                            "chunk_id": chunk_id,
                            "similarity_score": score,
                            "text": chunk_data["text"],
                            "metadata": chunk_data["metadata"],
                            "rank": 0,
                        }
                    )

        # Sort by score and take top_k
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = results[:top_k]

        # Update ranks
        for i, result in enumerate(results):
            result["rank"] = i + 1

        retrieved_content = [
            {
                "content": r["text"],
                "source": r["metadata"].get("file_name", "unknown"),
                "score": r["similarity_score"],
                "document_id": r["metadata"].get("document_id", "unknown"),
            }
            for r in results
        ]

        return {
            "query": query,
            "total_results": len(results),
            "retrieved_content": retrieved_content,
            "source_documents": list(
                set(r["metadata"].get("file_name", "unknown") for r in results)
            ),
            "search_method": "text_based",
        }

    def get_document_summary(self, document_id: str) -> Dict:
        """Get summary information about a specific document."""
        if document_id not in self.documents:
            return {"error": "Document not found"}

        doc_data = self.documents[document_id]
        chunk_count = sum(
            1 for chunk_data in self.chunks.values() if chunk_data["document_id"] == document_id
        )

        return {
            "document_id": document_id,
            "metadata": doc_data["metadata"],
            "chunk_count": chunk_count,
            "full_text_preview": (
                doc_data["full_text"][:500] + "..."
                if len(doc_data["full_text"]) > 500
                else doc_data["full_text"]
            ),
        }

    def get_index_stats(self) -> Dict:
        """Get comprehensive index statistics."""
        vector_store_info = "None"
        if self.chroma_collection is not None:
            vector_store_info = "ChromaDB"
        elif self.faiss_index is not None:
            vector_store_info = "FAISS (CPU)"

        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "embedding_model": (
                "sentence-transformers/all-MiniLM-L6-v2" if self.embedding_model else None
            ),
            "vector_store": vector_store_info,
            "semantic_search_available": self.embedding_model is not None,
            "collection_name": self.collection_name,
            "system_info": {
                "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE,
                "faiss_available": FAISS_AVAILABLE,
                "faiss_functional": FAISS_FUNCTIONAL,
                "chromadb_available": CHROMADB_AVAILABLE,
                "chromadb_functional": CHROMADB_FUNCTIONAL,
            },
        }

    def clear_index(self) -> Dict:
        """Clear all indexed documents."""
        try:
            self.documents.clear()
            self.chunks.clear()

            # Reset vector stores
            if self.chroma_collection is not None and self.chroma_client is not None:
                try:
                    self.chroma_client.delete_collection(self.collection_name)
                    self._setup_vector_store()
                except Exception as e:
                    logger.warning(f"Error deleting ChromaDB collection: {e}")

            elif self.faiss_index is not None:
                try:
                    self.faiss_index.reset()
                    self.chunk_ids.clear()
                except Exception as e:
                    logger.warning(f"Error resetting FAISS index: {e}")

            return {"success": True, "message": "Index cleared successfully"}

        except Exception as e:
            logger.error(f"Error clearing index: {e}")
            return {"error": str(e)}


# Global index instance
_pdf_index: Optional[LightweightPDFIndex] = None


def get_pdf_index() -> Optional[LightweightPDFIndex]:
    """Get or create the global PDF index instance."""
    global _pdf_index

    if _pdf_index is None:
        try:
            _pdf_index = LightweightPDFIndex()
        except Exception as e:
            logger.error(f"Failed to initialize PDF index: {e}")
            return None

    return _pdf_index


def cleanup_pdf_index():
    """Cleanup the PDF index."""
    global _pdf_index
    _pdf_index = None
