from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from app.database.database import get_db
from app.services.document_service import DocumentService
from app.security.jwt import get_current_user
from app.security.permissions import require_permission
from app.security.audit import log_audit_event
from app.config import settings
from app.utils.logger import logger

router = APIRouter()

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    file_type: str
    uploaded_by: int
    uploaded_at: str
    processed: bool
    chunk_count: Optional[int] = 0

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document for RAG processing"""
    try:
        # Validate file extension
        file_ext = f".{file.filename.split('.')[-1].lower()}"
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
        
        document_service = DocumentService(db)
        result = await document_service.upload_document(
            file=file,
            user_id=current_user.id,
            description=description
        )
        
        await log_audit_event(db, current_user.id, "document_uploaded", f"Uploaded: {file.filename}")
        logger.info(f"Document uploaded: {file.filename} by user {current_user.username}")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all uploaded documents"""
    try:
        document_service = DocumentService(db)
        documents = await document_service.get_documents(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        return documents
    except Exception as e:
        logger.error(f"Get documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    try:
        document_service = DocumentService(db)
        result = await document_service.delete_document(
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        await log_audit_event(db, current_user.id, "document_deleted", f"Deleted document ID: {document_id}")
        return {"message": "Document deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}/status")
async def get_document_status(
    document_id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get document processing status"""
    try:
        document_service = DocumentService(db)
        status = await document_service.get_document_status(document_id, current_user.id)
        if not status:
            raise HTTPException(status_code=404, detail="Document not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/reprocess")
async def reprocess_documents(
    document_ids: List[int],
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reprocess documents for RAG"""
    try:
        document_service = DocumentService(db)
        result = await document_service.reprocess_documents(
            document_ids=document_ids,
            user_id=current_user.id
        )
        
        await log_audit_event(db, current_user.id, "documents_reprocessed", f"Reprocessed {len(document_ids)} documents")
        return {"message": "Documents reprocessing started", "document_ids": document_ids}
    
    except Exception as e:
        logger.error(f"Reprocess error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))