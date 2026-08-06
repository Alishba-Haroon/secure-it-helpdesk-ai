from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.database import crud
from app.database.models import TicketStatus, TicketPriority
from app.security.audit import log_audit_event
from app.utils.logger import logger
from app.rag.chain import RAGChain

class TicketService:
    """Service for ticket management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag_chain = RAGChain()
    
    async def create_ticket(
        self,
        ticket_data: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """Create a new ticket"""
        try:
            # Add created_by
            ticket_data["created_by"] = user_id
            
            # Set default status if not provided
            if "status" not in ticket_data:
                ticket_data["status"] = "open"
            
            # Create ticket
            ticket = await crud.create_ticket(self.db, ticket_data)
            
            # Generate AI suggestion if description is provided
            if ticket.description:
                await self._generate_ticket_suggestions(ticket.id)
            
            logger.info(f"Ticket {ticket.id} created by user {user_id}")
            
            return self._format_ticket(ticket)
        
        except Exception as e:
            logger.error(f"Error creating ticket: {str(e)}")
            raise
    
    async def _generate_ticket_suggestions(self, ticket_id: int) -> None:
        """Generate AI suggestions for a ticket"""
        try:
            ticket = await crud.get_ticket_by_id(self.db, ticket_id)
            if not ticket:
                return
            
            # Generate classification
            classification_prompt = f"""
            Classify this IT support ticket:
            Title: {ticket.title}
            Description: {ticket.description}
            """
            
            # Use RAG to get suggestions
            result = await self.rag_chain.process_query(
                query=classification_prompt,
                top_k=3
            )
            
            # Update ticket with AI suggestions
            suggestions = {
                "ai_classification": result.get('response', ''),
                "ai_suggestions": result.get('sources', []),
                "ai_confidence": result.get('confidence_score', 0)
            }
            
            await crud.update_ticket(
                self.db,
                ticket_id,
                {"metadata": suggestions}
            )
        
        except Exception as e:
            logger.error(f"Error generating ticket suggestions: {str(e)}")
    
    async def get_tickets(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get tickets with filters"""
        try:
            tickets = await crud.get_tickets(
                self.db,
                user_id=user_id,
                status=status,
                priority=priority,
                skip=skip,
                limit=limit
            )
            
            return [self._format_ticket(ticket) for ticket in tickets]
        
        except Exception as e:
            logger.error(f"Error getting tickets: {str(e)}")
            return []
    
    async def get_ticket(self, ticket_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific ticket"""
        try:
            ticket = await crud.get_ticket_by_id(self.db, ticket_id)
            if not ticket:
                return None
            
            # Check permission
            user = await crud.get_user_by_id(self.db, user_id)
            if (ticket.created_by != user_id and 
                ticket.assigned_to != user_id and 
                user.role not in ["admin", "super_admin"]):
                return None
            
            return self._format_ticket(ticket, detailed=True)
        
        except Exception as e:
            logger.error(f"Error getting ticket {ticket_id}: {str(e)}")
            return None
    
    async def update_ticket(
        self,
        ticket_id: int,
        update_data: Dict[str, Any],
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Update a ticket"""
        try:
            ticket = await crud.get_ticket_by_id(self.db, ticket_id)
            if not ticket:
                return None
            
            # Check permission
            user = await crud.get_user_by_id(self.db, user_id)
            if (ticket.created_by != user_id and 
                ticket.assigned_to != user_id and 
                user.role not in ["admin", "super_admin"]):
                return None
            
            # Handle status changes
            new_status = update_data.get("status")
            if new_status == "resolved" and ticket.status != "resolved":
                update_data["resolved_at"] = datetime.now()
            elif new_status == "closed" and ticket.status != "closed":
                update_data["resolved_at"] = datetime.now() if not ticket.resolved_at else ticket.resolved_at
            
            # Update ticket
            updated_ticket = await crud.update_ticket(self.db, ticket_id, update_data)
            
            logger.info(f"Ticket {ticket_id} updated by user {user_id}")
            return self._format_ticket(updated_ticket) if updated_ticket else None
        
        except Exception as e:
            logger.error(f"Error updating ticket {ticket_id}: {str(e)}")
            return None
    
    async def delete_ticket(self, ticket_id: int, user_id: int) -> bool:
        """Delete a ticket"""
        try:
            ticket = await crud.get_ticket_by_id(self.db, ticket_id)
            if not ticket:
                return False
            
            # Check permission (only admin or creator can delete)
            user = await crud.get_user_by_id(self.db, user_id)
            if ticket.created_by != user_id and user.role not in ["admin", "super_admin"]:
                return False
            
            result = await crud.delete_ticket(self.db, ticket_id)
            
            if result:
                logger.info(f"Ticket {ticket_id} deleted by user {user_id}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error deleting ticket {ticket_id}: {str(e)}")
            return False
    
    async def assign_ticket(
        self,
        ticket_id: int,
        assignee_id: int,
        user_id: int
    ) -> bool:
        """Assign a ticket to a user"""
        try:
            ticket = await crud.get_ticket_by_id(self.db, ticket_id)
            if not ticket:
                return False
            
            # Check permission
            user = await crud.get_user_by_id(self.db, user_id)
            if user.role not in ["admin", "super_admin", "agent"]:
                return False
            
            # Update assignment
            updated_ticket = await crud.update_ticket(
                self.db,
                ticket_id,
                {"assigned_to": assignee_id}
            )
            
            if updated_ticket:
                logger.info(f"Ticket {ticket_id} assigned to user {assignee_id} by {user_id}")
            
            return bool(updated_ticket)
        
        except Exception as e:
            logger.error(f"Error assigning ticket {ticket_id}: {str(e)}")
            return False
    
    async def resolve_ticket(
        self,
        ticket_id: int,
        resolution: str,
        user_id: int
    ) -> bool:
        """Resolve a ticket"""
        try:
            ticket = await crud.get_ticket_by_id(self.db, ticket_id)
            if not ticket:
                return False
            
            # Check permission
            user = await crud.get_user_by_id(self.db, user_id)
            if (ticket.created_by != user_id and 
                ticket.assigned_to != user_id and 
                user.role not in ["admin", "super_admin"]):
                return False
            
            # Update ticket
            updated_ticket = await crud.update_ticket(
                self.db,
                ticket_id,
                {
                    "status": "resolved",
                    "resolved_at": datetime.now(),
                    "resolution": resolution
                }
            )
            
            if updated_ticket:
                logger.info(f"Ticket {ticket_id} resolved by user {user_id}")
            
            return bool(updated_ticket)
        
        except Exception as e:
            logger.error(f"Error resolving ticket {ticket_id}: {str(e)}")
            return False
    
    async def get_ticket_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get ticket statistics"""
        try:
            return await crud.get_ticket_statistics(self.db, user_id)
        
        except Exception as e:
            logger.error(f"Error getting ticket stats: {str(e)}")
            return {}
    
    def _format_ticket(self, ticket, detailed: bool = False) -> Dict[str, Any]:
        """Format ticket for response"""
        result = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status,
            "priority": ticket.priority,
            "category": ticket.category,
            "created_by": ticket.created_by,
            "assigned_to": ticket.assigned_to,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            "resolution": ticket.resolution
        }
        
        if detailed:
            result["metadata"] = ticket.metadata
            result["creator_username"] = ticket.creator.username if ticket.creator else None
            result["assignee_username"] = ticket.assignee.username if ticket.assignee else None
        
        return result