from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from app.database.database import get_db
from app.services.chat_service import ChatService
from app.security.jwt import get_current_user
from app.security.permissions import require_permission
from app.security.audit import log_audit_event
from app.utils.logger import logger

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[dict] = []
    confidence_score: float = 0.0

@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message and get AI response"""
    try:
        chat_service = ChatService(db)
        response = await chat_service.process_message(
            user_id=current_user.id,
            message=request.message,
            conversation_id=request.conversation_id,
            context=request.context
        )
        
        await log_audit_event(db, current_user.id, "chat_message", f"User sent message: {request.message[:50]}...")
        logger.info(f"Chat processed for user {current_user.username}")
        
        return response
    
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Stream chat response"""
    try:
        chat_service = ChatService(db)
        
        async def generate():
            async for chunk in chat_service.process_message_stream(
                user_id=current_user.id,
                message=request.message,
                conversation_id=request.conversation_id
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    except Exception as e:
        logger.error(f"Stream chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations")
async def get_conversations(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's conversation history"""
    try:
        chat_service = ChatService(db)
        conversations = await chat_service.get_user_conversations(current_user.id)
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Get conversations error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific conversation details"""
    try:
        chat_service = ChatService(db)
        conversation = await chat_service.get_conversation(
            conversation_id, 
            current_user.id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation"""
    try:
        chat_service = ChatService(db)
        result = await chat_service.delete_conversation(conversation_id, current_user.id)
        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        await log_audit_event(db, current_user.id, "conversation_deleted", f"Deleted conversation {conversation_id}")
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))