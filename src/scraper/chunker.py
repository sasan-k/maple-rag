"""
Content chunking for RAG.

Splits documents into smaller chunks for efficient retrieval.
"""

from dataclasses import dataclass
from typing import Any

from src.config.settings import get_settings


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""

    content: str
    chunk_index: int
    metadata: dict[str, Any]


class RecursiveTextSplitter:
    """
    Simple recursive text splitter.
    
    Pure Python implementation to avoid dependency issues.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",  # Paragraph breaks
            "\n",  # Line breaks
            ". ",  # Sentence breaks
            "? ",
            "! ",
            "; ",
            ", ",  # Clause breaks
            " ",  # Word breaks
            "",  # Character breaks (last resort)
        ]

    def _split_text_with_separator(
        self, text: str, separator: str
    ) -> list[str]:
        """Split text by separator."""
        if separator:
            return text.split(separator)
        # Empty separator means split by character
        return list(text)

    def _merge_splits(
        self, splits: list[str], separator: str
    ) -> list[str]:
        """Merge splits into chunks of appropriate size."""
        chunks = []
        current_chunk: list[str] = []
        current_length = 0

        for split in splits:
            split_length = len(split) + len(separator)

            if current_length + split_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = separator.join(current_chunk)
                chunks.append(chunk_text)

                # Start new chunk with overlap
                overlap_length = 0
                overlap_splits = []
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_splits.insert(0, s)
                        overlap_length += len(s) + len(separator)
                    else:
                        break

                current_chunk = overlap_splits
                current_length = sum(len(s) + len(separator) for s in current_chunk)

            current_chunk.append(split)
            current_length += split_length

        # Add final chunk
        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return chunks

    def _split_recursive(
        self, text: str, separators: list[str]
    ) -> list[str]:
        """Recursively split text using separators."""
        if not separators:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        splits = self._split_text_with_separator(text, separator)

        # Filter out empty splits
        splits = [s for s in splits if s.strip()]

        if not splits:
            return []

        # Merge splits into chunks
        chunks = self._merge_splits(splits, separator)

        # Recursively split chunks that are too large
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size and remaining_separators:
                # Try splitting with next separator
                sub_chunks = self._split_recursive(chunk, remaining_separators)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        return final_chunks

    def split_text(self, text: str) -> list[str]:
        """Split text into chunks."""
        if not text or not text.strip():
            return []
        return self._split_recursive(text, self.separators)


class ContentChunker:
    """
    Splits content into chunks for embedding and retrieval.

    Uses recursive character splitting with semantic separators.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        """
        Initialize the chunker.

        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks for context preservation
        """
        settings = get_settings()

        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self.splitter = RecursiveTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def chunk_text(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """
        Split text content into chunks.

        Args:
            content: The text content to split
            metadata: Base metadata to include with each chunk

        Returns:
            List of Chunk objects
        """
        if not content or not content.strip():
            return []

        chunks = self.splitter.split_text(content)

        return [
            Chunk(
                content=chunk_text,
                chunk_index=i,
                metadata={
                    **(metadata or {}),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk_text),
                },
            )
            for i, chunk_text in enumerate(chunks)
        ]

    def chunk_document(
        self,
        content: str,
        url: str,
        title: str,
        language: str = "en",
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """
        Chunk a document with standard metadata.

        Args:
            content: Document text content
            url: Source URL
            title: Document title
            language: Document language (en/fr)
            extra_metadata: Additional metadata to include

        Returns:
            List of Chunk objects with document metadata
        """
        base_metadata = {
            "url": url,
            "title": title,
            "language": language,
            **(extra_metadata or {}),
        }

        return self.chunk_text(content, base_metadata)

