"""Data models for document chunking."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""

    source_document_id: str
    source_tab: str | None = None
    source_section: str | None = None
    chunk_index: int = 0
    total_chunks: int = 0
    start_position: int = 0
    end_position: int = 0
    overlap_before: int = 0
    overlap_after: int = 0
    heading_level: int = 0
    contains_question: bool = False
    estimated_tokens: int = 0
    custom_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """A chunk of document content with metadata."""

    content: str
    summary: str | None = None
    embedding: list[float] | None = None
    metadata: ChunkMetadata | None = None

    def __len__(self) -> int:
        """Return the length of the content."""
        return len(self.content)

    def get_token_count(self) -> int:
        """Estimate token count for the chunk."""
        # Rough estimate: 1 token ≈ 4 characters for English text
        return len(self.content) // 4

    def get_word_count(self) -> int:
        """Get word count for the chunk."""
        return len(self.content.split())
