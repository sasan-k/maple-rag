"""
Document repository for managing documents and chunks.
"""

import hashlib
import uuid
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document, DocumentChunk


class DocumentRepository:
    """Repository for document operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with a database session."""
        self.session = session

    @staticmethod
    def generate_id() -> str:
        """Generate a unique document ID."""
        return str(uuid.uuid4())

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def get_by_id(self, doc_id: str) -> Document | None:
        """Get a document by ID."""
        result = await self.session.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_by_url(self, url: str) -> Document | None:
        """Get a document by URL."""
        result = await self.session.execute(
            select(Document).where(Document.url == url)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        url: str,
        title: str,
        content: str,
        language: str = "en",
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Create a new document."""
        doc = Document(
            id=self.generate_id(),
            url=url,
            title=title,
            content=content,
            content_hash=self.compute_hash(content),
            language=language,
            metadata_=metadata or {},
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def update(
        self,
        doc_id: str,
        title: str | None = None,
        content: str | None = None,
        language: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document | None:
        """Update an existing document."""
        doc = await self.get_by_id(doc_id)
        if not doc:
            return None

        if title is not None:
            doc.title = title
        if content is not None:
            doc.content = content
            doc.content_hash = self.compute_hash(content)
        if language is not None:
            doc.language = language
        if metadata is not None:
            doc.metadata_ = metadata

        await self.session.flush()
        return doc

    async def upsert(
        self,
        url: str,
        title: str,
        content: str,
        language: str = "en",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[Document, bool]:
        """
        Create or update a document.

        Returns:
            Tuple of (document, was_created)
        """
        existing = await self.get_by_url(url)

        if existing:
            # Check if content changed
            new_hash = self.compute_hash(content)
            if existing.content_hash == new_hash:
                return existing, False  # No change

            # Update existing
            existing.title = title
            existing.content = content
            existing.content_hash = new_hash
            existing.language = language
            if metadata:
                existing.metadata_ = metadata
            await self.session.flush()
            return existing, False

        # Create new
        doc = await self.create(url, title, content, language, metadata)
        return doc, True

    async def delete(self, doc_id: str) -> bool:
        """Delete a document and its chunks."""
        result = await self.session.execute(
            delete(Document).where(Document.id == doc_id)
        )
        return result.rowcount > 0

    async def list_all(
        self, language: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Document]:
        """List all documents with optional language filter."""
        query = select(Document)

        if language:
            query = query.where(Document.language == language)

        query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_chunks(self, doc_id: str) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        result = await self.session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def add_chunk(
        self,
        document_id: str,
        content: str,
        embedding: list[float],
        chunk_index: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentChunk:
        """Add a chunk to a document."""
        chunk = DocumentChunk(
            id=self.generate_id(),
            document_id=document_id,
            content=content,
            embedding=embedding,
            chunk_index=chunk_index,
            metadata_=metadata or {},
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def add_chunks_batch(
        self,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> list[DocumentChunk]:
        """
        Add multiple chunks to a document in batch.

        Args:
            document_id: The document ID
            chunks: List of dicts with keys: content, embedding, chunk_index, metadata
        """
        chunk_objects = []
        for chunk_data in chunks:
            chunk = DocumentChunk(
                id=self.generate_id(),
                document_id=document_id,
                content=chunk_data["content"],
                embedding=chunk_data["embedding"],
                chunk_index=chunk_data.get("chunk_index", 0),
                metadata_=chunk_data.get("metadata", {}),
            )
            chunk_objects.append(chunk)
            self.session.add(chunk)

        await self.session.flush()
        return chunk_objects

    async def delete_chunks(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        result = await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return result.rowcount

    async def similarity_search(
        self,
        embedding: list[float],
        k: int = 5,
        language: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Perform similarity search using pgvector.

        Args:
            embedding: Query embedding vector
            k: Number of results to return
            language: Optional language filter

        Returns:
            List of (chunk, similarity_score) tuples
        """
        # Build the query using cosine distance
        # pgvector: <=> is cosine distance
        # Format embedding as PostgreSQL array string
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        if language:
            query = text("""
                SELECT dc.*, 1 - (dc.embedding <=> CAST(:embedding AS vector)) as similarity
                FROM canadaca.document_chunks dc
                JOIN canadaca.documents d ON dc.document_id = d.id
                WHERE d.language = :language
                ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                LIMIT :k
            """).bindparams(embedding=embedding_str, language=language, k=k)
            result = await self.session.execute(query)
        else:
            query = text("""
                SELECT dc.*, 1 - (dc.embedding <=> CAST(:embedding AS vector)) as similarity
                FROM canadaca.document_chunks dc
                ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                LIMIT :k
            """).bindparams(embedding=embedding_str, k=k)
            result = await self.session.execute(query)

        rows = result.fetchall()
        chunks_with_scores = []

        for row in rows:
            chunk = DocumentChunk(
                id=row.id,
                document_id=row.document_id,
                content=row.content,
                embedding=row.embedding,
                chunk_index=row.chunk_index,
                metadata_=row.metadata,
                created_at=row.created_at,
            )
            chunks_with_scores.append((chunk, row.similarity))

        return chunks_with_scores

    async def get_document_count(self) -> int:
        """Get total document count."""
        result = await self.session.execute(
            text("SELECT COUNT(*) FROM canadaca.documents")
        )
        return result.scalar() or 0

    async def get_chunk_count(self) -> int:
        """Get total chunk count."""
        result = await self.session.execute(
            text("SELECT COUNT(*) FROM canadaca.document_chunks")
        )
        return result.scalar() or 0
