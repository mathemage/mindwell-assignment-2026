"""Admin routes for document management."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_admin_user
from app.api.schemas.schemas import (
    DocumentListItem,
    DocumentResponse,
    DocumentUploadResponse,
    ReindexResponse,
)
from app.core.logging import get_logger
from app.db.connection import get_db
from app.db.models import User
from app.services.document_service import DocumentService

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/docs", tags=["admin"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    doc_service: DocumentService = Depends(),
) -> DocumentUploadResponse:
    """
    Upload a document to the knowledge base.

    Supported formats:
    - Markdown (.md)
    - PDF (.pdf)
    - Plain text (.txt)

    The document will be:
    1. Chunked into smaller pieces
    2. Embedded using the configured embedding model
    3. Stored in the vector database
    """
    logger.info("Document upload", filename=file.filename, user_id=current_user.id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        content = await file.read()
        document = await doc_service.ingest_file(db, file.filename, content)

        # Count chunks
        chunk_count = len(document.chunks)

        return DocumentUploadResponse(
            id=document.id,
            title=document.title,
            source_type=document.source_type,
            chunk_count=chunk_count,
            created_at=document.created_at,
        )

    except Exception as e:
        logger.error("Document upload failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=list[DocumentListItem])
def list_documents(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    doc_service: DocumentService = Depends(),
) -> list[DocumentListItem]:
    """List documents in the knowledge base."""
    documents = doc_service.list_documents(db, limit, offset)
    return [
        DocumentListItem(
            id=doc.id,
            title=doc.title,
            source_type=doc.source_type,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    doc_service: DocumentService = Depends(),
) -> DocumentResponse:
    """Get a specific document."""
    document = doc_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        title=document.title,
        source_type=document.source_type,
        content=document.content,
        metadata=document.extra_metadata,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.post("/{document_id}/reindex", response_model=ReindexResponse)
async def reindex_document(
    document_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    doc_service: DocumentService = Depends(),
) -> ReindexResponse:
    """
    Re-index a document (regenerate chunks and embeddings).

    Useful when:
    - Chunking strategy has changed
    - Embedding model has been updated
    - Document metadata needs to be refreshed
    """
    logger.info("Document reindex", document_id=document_id, user_id=current_user.id)

    try:
        document = await doc_service.reindex_document(db, document_id)
        chunk_count = len(document.chunks)

        return ReindexResponse(
            document_id=document.id,
            chunk_count=chunk_count,
            message=f"Document re-indexed successfully with {chunk_count} chunks",
        )

    except Exception as e:
        logger.error("Document reindex failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
