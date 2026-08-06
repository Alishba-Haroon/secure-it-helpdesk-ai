from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.database.database import get_db
from app.services.ticket_service import TicketService
from app.security.jwt import get_current_user
from app.security.permissions import require_permission
from app.security.audit import log_audit_event
from app.utils.logger import logger

router = APIRouter()

class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = Field(..., pattern="^(low|medium|high|critical)$")
    category: str
    assigned_to: Optional[int] = None

class TicketUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(open|in_progress|resolved|closed)$")  # ✅ Changed
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")  # ✅ Changed
    assigned_to: Optional[int] = None
    resolution: Optional[str] = None

class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    category: str
    created_by: int
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    ticket_data: TicketCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new support ticket"""
    try:
        ticket_service = TicketService(db)
        ticket = await ticket_service.create_ticket(
            ticket_data=ticket_data.dict(),
            user_id=current_user.id
        )
        
        await log_audit_event(db, current_user.id, "ticket_created", f"Created ticket: {ticket['title']}")
        logger.info(f"Ticket created by user {current_user.username}: {ticket['title']}")
        
        return ticket
    
    except Exception as e:
        logger.error(f"Create ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tickets", response_model=List[TicketResponse])
async def get_tickets(
    status: Optional[str] = Query(None, pattern="^(open|in_progress|resolved|closed)$"),  # ✅ Changed
    priority: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),  # ✅ Changed
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tickets with filters"""
    try:
        ticket_service = TicketService(db)
        tickets = await ticket_service.get_tickets(
            user_id=current_user.id,
            status=status,
            priority=priority,
            skip=skip,
            limit=limit
        )
        return tickets
    except Exception as e:
        logger.error(f"Get tickets error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific ticket"""
    try:
        ticket_service = TicketService(db)
        ticket = await ticket_service.get_ticket(ticket_id, current_user.id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return ticket
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a ticket"""
    try:
        ticket_service = TicketService(db)
        ticket = await ticket_service.update_ticket(
            ticket_id=ticket_id,
            update_data=ticket_data.dict(exclude_unset=True),
            user_id=current_user.id
        )
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        await log_audit_event(db, current_user.id, "ticket_updated", f"Updated ticket ID: {ticket_id}")
        logger.info(f"Ticket updated: {ticket_id} by user {current_user.username}")
        
        return ticket
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a ticket"""
    try:
        ticket_service = TicketService(db)
        result = await ticket_service.delete_ticket(ticket_id, current_user.id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        await log_audit_event(db, current_user.id, "ticket_deleted", f"Deleted ticket ID: {ticket_id}")
        return {"message": "Ticket deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: int,
    assignee_id: int,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign a ticket to a user"""
    try:
        ticket_service = TicketService(db)
        result = await ticket_service.assign_ticket(
            ticket_id=ticket_id,
            assignee_id=assignee_id,
            user_id=current_user.id
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        await log_audit_event(db, current_user.id, "ticket_assigned", f"Assigned ticket {ticket_id} to user {assignee_id}")
        return {"message": "Ticket assigned successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assign ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: int,
    resolution: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resolve a ticket"""
    try:
        ticket_service = TicketService(db)
        result = await ticket_service.resolve_ticket(
            ticket_id=ticket_id,
            resolution=resolution,
            user_id=current_user.id
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        await log_audit_event(db, current_user.id, "ticket_resolved", f"Resolved ticket {ticket_id}")
        return {"message": "Ticket resolved successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve ticket error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))