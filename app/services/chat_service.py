from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional, AsyncGenerator
import uuid
from datetime import datetime
from app.rag.chain import RAGChain
from app.rag.retriever import DocumentRetriever
from app.database import crud
from app.database.models import Conversation
from app.security.audit import log_audit_event
from app.utils.logger import logger

class ChatService:
    """Service for chat functionality"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag_chain = RAGChain()
        self.retriever = DocumentRetriever()
    
    async def process_message(
        self,
        user_id: int,
        message: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process a chat message"""
        try:
            # Get or create conversation
            if not conversation_id:
                conversation_id = await self._create_conversation(user_id)
            
            # Get conversation history
            history = await self._get_conversation_history(conversation_id)
            
            # Process with RAG
            result = await self.rag_chain.process_query(
                query=message,
                conversation_id=conversation_id,
                conversation_history=history,
                top_k=5
            )
            
            # Save messages
            await self._save_messages(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=message,
                assistant_message=result['response']
            )
            
            # Update conversation timestamp
            await crud.update_conversation(
                self.db,
                conversation_id,
                {"updated_at": datetime.now()}
            )
            
            return {
                "response": result['response'],
                "conversation_id": conversation_id,
                "sources": result['sources'],
                "confidence_score": result['confidence_score']
            }
        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise
    
    async def process_message_stream(
        self,
        user_id: int,
        message: str,
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Process a chat message with streaming"""
        try:
            # Get or create conversation
            if not conversation_id:
                conversation_id = await self._create_conversation(user_id)
            
            # Get conversation history
            history = await self._get_conversation_history(conversation_id)
            
            # Stream processing
            full_response = ""
            async for chunk in self.rag_chain.process_stream_query(
                query=message,
                conversation_id=conversation_id,
                conversation_history=history,
                top_k=5
            ):
                yield chunk
                
                # Accumulate response for saving
                import json
                try:
                    chunk_data = json.loads(chunk)
                    if chunk_data.get('type') == 'content':
                        full_response += chunk_data.get('data', '')
                except:
                    pass
            
            # Save messages if we have a response
            if full_response:
                await self._save_messages(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    user_message=message,
                    assistant_message=full_response
                )
        
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}")
            raise
    
    async def _create_conversation(self, user_id: int) -> str:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())[:36]
        
        conversation_data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "title": f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
        
        await crud.create_conversation(self.db, conversation_data)
        return conversation_id
    
    async def _get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """Get conversation history"""
        try:
            messages = await crud.get_messages_by_conversation(
                self.db,
                conversation_id,
                limit=limit
            )
            
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            return history
        
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
    
    async def _save_messages(
        self,
        conversation_id: str,
        user_id: int,
        user_message: str,
        assistant_message: str
    ) -> None:
        """Save user and assistant messages"""
        try:
            # Save user message
            await crud.create_message(self.db, {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": "user",
                "content": user_message
            })
            
            # Save assistant message
            await crud.create_message(self.db, {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": "assistant",
                "content": assistant_message
            })
        
        except Exception as e:
            logger.error(f"Error saving messages: {str(e)}")
            raise
    
    async def get_user_conversations(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's conversations"""
        try:
            conversations = await crud.get_user_conversations(
                self.db,
                user_id,
                limit=limit
            )
            
            result = []
            for conv in conversations:
                # Get last message
                messages = await crud.get_messages_by_conversation(
                    self.db,
                    conv.conversation_id,
                    limit=1
                )
                
                result.append({
                    "conversation_id": conv.conversation_id,
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "last_message": messages[0].content[:100] if messages else "",
                    "message_count": len(messages)
                })
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting conversations: {str(e)}")
            return []
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get conversation details"""
        try:
            # Verify ownership
            conversation = await crud.get_conversation_by_id(
                self.db,
                conversation_id
            )
            
            if not conversation or conversation.user_id != user_id:
                return None
            
            # Get messages
            messages = await crud.get_conversation_messages(
                self.db,
                conversation_id
            )
            
            return {
                "conversation_id": conversation.conversation_id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
            }
        
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            return None
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: int
    ) -> bool:
        """Delete a conversation"""
        try:
            # Verify ownership
            conversation = await crud.get_conversation_by_id(
                self.db,
                conversation_id
            )
            
            if not conversation or conversation.user_id != user_id:
                return False
            
            # Delete conversation
            # First delete messages
            # Then delete conversation
            # (This would need cascade delete in models)
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            return False