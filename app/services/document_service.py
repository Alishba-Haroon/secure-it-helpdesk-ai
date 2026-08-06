from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from fastapi import UploadFile
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from app.database import crud
from app.rag.loader import DocumentLoader
from app.rag.splitter import DocumentSplitter
from app.rag.embeddings import EmbeddingService
from app.rag.retriever import DocumentRetriever
from app.config import settings
from app.security.audit import log_audit_event
from app.utils.logger import logger

class DocumentService:
    """Service for document management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.loader = DocumentLoader()
        self.splitter = DocumentSplitter()
        self.embedding_service = EmbeddingService()
        self.retriever = DocumentRetriever()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_document(
        self,
        file: UploadFile,
        user_id: int,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload and process a document"""
        try:
            # Validate file
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in settings.ALLOWED_EXTENSIONS:
                raise ValueError(f"File type {file_ext} not allowed")
            
            # Read file content
            content = await file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE:
                raise ValueError(f"File too large. Max size: {settings.MAX_UPLOAD_SIZE} bytes")
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            file_path = self.upload_dir / unique_filename
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Create document record
            document_data = {
                "filename": file.filename,
                "file_path": str(file_path),
                "file_size": len(content),
                "file_type": file_ext[1:],  # Remove dot
                "description": description,
                "uploaded_by": user_id,
                "processing_status": "pending"
            }
            
            document = await crud.create_document(self.db, document_data)
            
            # Process document in background
            await self._process_document(document.id)
            
            return {
                "id": document.id,
                "filename": document.filename,
                "file_size": document.file_size,
                "file_type": document.file_type,
                "uploaded_at": document.uploaded_at.isoformat(),
                "processing_status": "pending",
                "message": "Document uploaded successfully. Processing started."
            }
        
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise
    
    async def _process_document(self, document_id: int) -> None:
        """Process a document for RAG"""
        try:
            # Update status
            await crud.update_document(
                self.db,
                document_id,
                {"processing_status": "processing"}
            )
            
            # Get document
            document = await crud.get_document_by_id(self.db, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Load document
            file_path = document.file_path
            loaded_docs = await self.loader.load_file(file_path)
            
            # Split into chunks
            chunks = await self.splitter.split_documents(loaded_docs)
            
            # Generate embeddings and add to vector DB
            chunk_texts = [chunk['content'] for chunk in chunks]
            embeddings = await self.embedding_service.generate_embeddings(chunk_texts)
            
            # Prepare for vector DB
            vector_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk['embedding'] = embedding
                chunk['metadata']['document_id'] = document_id
                chunk['metadata']['chunk_index'] = i
                vector_chunks.append(chunk)
            
            # Add to vector database
            import uuid
            vector_ids = [str(uuid.uuid4()) for _ in vector_chunks]
            await self.retriever.add_documents(vector_chunks, vector_ids)
            
            # Update document record
            await crud.update_document(
                self.db,
                document_id,
                {
                    "processed": True,
                    "processing_status": "completed",
                    "chunk_count": len(chunks),
                    "vector_ids": vector_ids
                }
            )
            
            logger.info(f"Document {document_id} processed successfully with {len(chunks)} chunks")
        
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            await crud.update_document(
                self.db,
                document_id,
                {"processing_status": "failed"}
            )
    
    async def get_documents(
        self,
        user_id: Optional[int] = None,
        processed: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of documents"""
        try:
            documents = await crud.get_documents(
                self.db,
                user_id=user_id,
                processed=processed,
                skip=skip,
                limit=limit
            )
            
            return [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_size": doc.file_size,
                    "file_type": doc.file_type,
                    "description": doc.description,
                    "uploaded_by": doc.uploaded_by,
                    "uploaded_at": doc.uploaded_at.isoformat(),
                    "processed": doc.processed,
                    "processing_status": doc.processing_status,
                    "chunk_count": doc.chunk_count
                }
                for doc in documents
            ]
        
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            return []
    
    async def get_document(self, document_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get document details"""
        try:
            document = await crud.get_document_by_id(self.db, document_id)
            if not document:
                return None
            
            # Check permission
            user = await crud.get_user_by_id(self.db, user_id)
            if document.uploaded_by != user_id and user.role not in ["admin", "super_admin"]:
                return None
            
            return {
                "id": document.id,
                "filename": document.filename,
                "file_path": document.file_path,
                "file_size": document.file_size,
                "file_type": document.file_type,
                "description": document.description,
                "uploaded_by": document.uploaded_by,
                "uploaded_at": document.uploaded_at.isoformat(),
                "processed": document.processed,
                "processing_status": document.processing_status,
                "chunk_count": document.chunk_count,
                "vector_ids": document.vector_ids
            }
        
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return None
    
    async def delete_document(self, document_id: int, user_id: int) -> bool:
        """Delete a document"""
        try:
            document = await crud.get_document_by_id(self.db, document_id)
            if not document:
                return False
            
            # Check permission
            user = await crud.get_user_by_id(self.db, user_id)
            if document.uploaded_by != user_id and user.role not in ["admin", "super_admin"]:
                return False
            
            # Delete from vector DB
            if document.vector_ids:
                await self.retriever.delete_documents(document.vector_ids)
            
            # Delete physical file
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
            
            # Delete from database
            await crud.delete_document(self.db, document_id)
            
            logger.info(f"Document {document_id} deleted by user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False
    
    async def get_document_status(self, document_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get document processing status"""
        try:
            document = await crud.get_document_by_id(self.db, document_id)
            if not document:
                return None
            
            # Check permission
            user = await crud.get_user_by_id(self.db, user_id)
            if document.uploaded_by != user_id and user.role not in ["admin", "super_admin"]:
                return None
            
            return {
                "id": document.id,
                "filename": document.filename,
                "processed": document.processed,
                "processing_status": document.processing_status,
                "chunk_count": document.chunk_count,
                "uploaded_at": document.uploaded_at.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error getting document status {document_id}: {str(e)}")
            return None
    
    async def reprocess_documents(
        self,
        document_ids: List[int],
        user_id: int
    ) -> Dict[str, Any]:
        """Reprocess documents for RAG"""
        try:
            user = await crud.get_user_by_id(self.db, user_id)
            if user.role not in ["admin", "super_admin"]:
                raise ValueError("Only admins can reprocess documents")
            
            processed = []
            failed = []
            
            for doc_id in document_ids:
                try:
                    # Reset document
                    await crud.update_document(
                        self.db,
                        doc_id,
                        {
                            "processed": False,
                            "processing_status": "pending",
                            "chunk_count": 0,
                            "vector_ids": []
                        }
                    )
                    
                    # Process again
                    await self._process_document(doc_id)
                    processed.append(doc_id)
                
                except Exception as e:
                    logger.error(f"Failed to reprocess document {doc_id}: {str(e)}")
                    failed.append(doc_id)
            
            return {
                "processed": processed,
                "failed": failed,
                "total": len(document_ids)
            }
        
        except Exception as e:
            logger.error(f"Error reprocessing documents: {str(e)}")
            raise