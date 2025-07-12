"""Vector database implementation using ChromaDB."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import chromadb
from chromadb import Collection, QueryResult
from chromadb.config import Settings as ChromaSettings

from app.chunking.models import Chunk
from app.config import get_settings

logger = logging.getLogger(__name__)


class VectorDatabase(ABC):
    """Abstract base class for vector databases."""

    @abstractmethod
    async def create_collection(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Create a new collection."""
        pass

    @abstractmethod
    async def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        pass

    @abstractmethod
    async def add_chunks(self, collection_name: str, chunks: list[Chunk]) -> None:
        """Add chunks to a collection."""
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        limit: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar chunks."""
        pass

    @abstractmethod
    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get statistics about a collection."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the database is healthy."""
        pass


class ChromaVectorDatabase(VectorDatabase):
    """ChromaDB implementation of vector database."""

    def __init__(self, host: str | None = None, port: int | None = None):
        """Initialize ChromaDB client.

        Args:
            host: ChromaDB host (optional, uses config if not provided)
            port: ChromaDB port (optional, uses config if not provided)
        """
        if host is None or port is None:
            settings = get_settings()
            host = host or settings.chroma_host
            port = port or settings.chroma_port

        self.host = host
        self.port = port
        self.chroma_url = f"http://{host}:{port}"

        # Initialize ChromaDB client
        try:
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            logger.info(f"Connected to ChromaDB at {self.chroma_url}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB at {self.chroma_url}: {e}")
            raise

    async def create_collection(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Create a new collection in ChromaDB."""
        try:
            # Delete existing collection if it exists
            try:
                await self.delete_collection(name)
                logger.info(f"Deleted existing collection: {name}")
            except Exception:
                pass  # Collection doesn't exist, which is fine

            # Create new collection
            collection = self.client.create_collection(
                name=name,
                metadata=metadata or {},
                embedding_function=None,  # We'll provide embeddings manually
            )
            logger.info(f"Created collection: {name}")

        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise

    async def delete_collection(self, name: str) -> None:
        """Delete a collection from ChromaDB."""
        try:
            self.client.delete_collection(name=name)
            logger.info(f"Deleted collection: {name}")
        except Exception as e:
            logger.warning(f"Failed to delete collection {name}: {e}")
            # Don't raise - collection might not exist

    async def add_chunks(self, collection_name: str, chunks: list[Chunk]) -> None:
        """Add chunks to a ChromaDB collection."""
        if not chunks:
            logger.warning("No chunks provided to add")
            return

        try:
            collection = self.client.get_collection(name=collection_name)

            # Prepare data for ChromaDB
            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                if chunk.embedding is None:
                    logger.warning(f"Chunk {i} has no embedding, skipping")
                    continue

                # Generate unique ID
                chunk_id = f"chunk_{i}_{hash(chunk.content[:100])}"
                ids.append(chunk_id)

                # Add embedding
                embeddings.append(chunk.embedding)

                # Add document content
                documents.append(chunk.content)

                # Prepare metadata
                metadata = {
                    "chunk_index": i,
                    "content_length": len(chunk.content),
                    "word_count": chunk.get_word_count(),
                    "token_count": chunk.get_token_count(),
                }

                # Add chunk metadata if available
                if chunk.metadata:
                    metadata.update(
                        {
                            "source_document_id": chunk.metadata.source_document_id,
                            "source_tab": chunk.metadata.source_tab or "Untitled Tab",
                            "source_tab_id": chunk.metadata.source_tab_id,  # Add missing tab ID
                            "source_section": chunk.metadata.source_section or "Untitled Section",
                            "heading_level": chunk.metadata.heading_level,
                            "contains_question": chunk.metadata.contains_question,
                            "estimated_tokens": chunk.metadata.estimated_tokens,
                        }
                    )

                # Add summary if available
                if chunk.summary:
                    metadata["summary"] = chunk.summary

                metadatas.append(metadata)

            # Add to ChromaDB
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(f"Added {len(ids)} chunks to collection {collection_name}")

        except Exception as e:
            logger.error(f"Failed to add chunks to collection {collection_name}: {e}")
            raise

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        limit: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar chunks in ChromaDB."""
        try:
            collection = self.client.get_collection(name=collection_name)

            # Perform similarity search
            results: QueryResult = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=metadata_filter,
                include=["documents", "metadatas", "distances"],
            )

            # Format results
            search_results = []
            if results["ids"] and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    result = {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0.0,
                        "similarity": 1.0
                        - (results["distances"][0][i] if results["distances"] else 0.0),
                    }
                    search_results.append(result)

            logger.info(f"Found {len(search_results)} results for query in {collection_name}")
            return search_results

        except Exception as e:
            logger.error(f"Failed to search collection {collection_name}: {e}")
            raise

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get statistics about a ChromaDB collection."""
        try:
            collection = self.client.get_collection(name=collection_name)

            # Get collection info
            count = collection.count()
            collection_metadata = collection.metadata

            # Get sample of documents to analyze
            sample_results = collection.get(limit=100, include=["metadatas"])

            stats = {
                "name": collection_name,
                "total_chunks": count,
                "collection_metadata": collection_metadata,
            }

            # Analyze metadata if available
            if sample_results["metadatas"]:
                metadatas = sample_results["metadatas"]

                # Count questions
                question_count = sum(1 for m in metadatas if m.get("contains_question", False))

                # Count unique sources
                unique_tabs = set(m.get("source_tab") for m in metadatas if m.get("source_tab"))
                unique_sections = set(
                    m.get("source_section") for m in metadatas if m.get("source_section")
                )

                # Average lengths
                avg_content_length = sum(m.get("content_length", 0) for m in metadatas) / len(
                    metadatas
                )
                avg_tokens = sum(m.get("estimated_tokens", 0) for m in metadatas) / len(metadatas)

                stats.update(
                    {
                        "chunks_with_questions": question_count,
                        "unique_tabs": len(unique_tabs),
                        "unique_sections": len(unique_sections),
                        "average_content_length": avg_content_length,
                        "average_tokens": avg_tokens,
                        "sample_size": len(metadatas),
                    }
                )

            return stats

        except Exception as e:
            logger.error(f"Failed to get stats for collection {collection_name}: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if ChromaDB is healthy and accessible."""
        try:
            # Try to get version or list collections
            self.client.heartbeat()
            return True
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
            return False

    def list_collections(self) -> list[str]:
        """List all collections in ChromaDB."""
        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
