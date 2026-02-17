"""Text chunking utilities."""

import re
from typing import Any

import tiktoken

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class TextChunker:
    """Text chunking utility."""

    def __init__(
        self,
        chunk_size: int = settings.chunk_size,
        chunk_overlap: int = settings.chunk_overlap,
    ):
        """
        Initialize chunker.

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Tiktoken may fail in offline environments
            self.encoding = None

    def chunk_markdown(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Chunk markdown text by headings.

        Args:
            text: Markdown text
            metadata: Optional metadata

        Returns:
            List of chunks with metadata
        """
        chunks = []
        metadata = metadata or {}

        # Split by headings (match at start of string or after newline)
        sections = re.split(r'(?:^|\n)(#{1,6})\s+(.+)\n', text, flags=re.MULTILINE)

        current_heading = ""
        current_level = 0
        current_text = sections[0] if sections else ""

        for i in range(1, len(sections), 3):
            if i + 1 < len(sections):
                heading_markers = sections[i]
                heading_text = sections[i + 1]
                section_text = sections[i + 2] if i + 2 < len(sections) else ""

                # Process previous section
                if current_text.strip():
                    section_chunks = self._split_long_text(current_text)
                    for _idx, chunk in enumerate(section_chunks):
                        chunks.append({
                            "text": chunk,
                            "metadata": {
                                **metadata,
                                "heading": current_heading,
                                "heading_level": current_level,
                                "section_index": len(chunks),
                            },
                        })

                # Update current heading
                current_level = len(heading_markers)
                current_heading = heading_text.strip()
                current_text = section_text

        # Process last section
        if current_text.strip():
            section_chunks = self._split_long_text(current_text)
            for _idx, chunk in enumerate(section_chunks):
                chunks.append({
                    "text": chunk,
                    "metadata": {
                        **metadata,
                        "heading": current_heading,
                        "heading_level": current_level,
                        "section_index": len(chunks),
                    },
                })

        logger.info("Chunked markdown", total_chunks=len(chunks))
        return chunks

    def chunk_text(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Chunk plain text by size.

        Args:
            text: Plain text
            metadata: Optional metadata

        Returns:
            List of chunks with metadata
        """
        metadata = metadata or {}
        chunks = self._split_long_text(text)

        result = [
            {
                "text": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": idx,
                },
            }
            for idx, chunk in enumerate(chunks)
        ]

        logger.info("Chunked text", total_chunks=len(result))
        return result

    def _split_long_text(self, text: str) -> list[str]:
        """
        Split long text into chunks.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending
                sentence_ends = ['. ', '! ', '? ', '\n\n']
                best_end = end

                for i in range(end, max(start + self.chunk_size // 2, start), -1):
                    if any(text[i:i+2].startswith(se) for se in sentence_ends):
                        best_end = i + 1
                        break

                end = best_end

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = end - self.chunk_overlap if end < len(text) else end

        return chunks
