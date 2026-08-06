from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.sql import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.database.models import (
    User, Ticket, Document, Message, Conversation,
    AuditLog, KnowledgeBase, TicketStatus, TicketPriority
)
from app.security.encryption import verify_password, hash_password
from app.utils.logger import logger

# User CRUD operations
async def create_user(db: AsyncSession, user_data: Dict[str, Any]) -> User:
    """Create a new user"""
    user = User(**user_data)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username"""
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate user"""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    user.last_login = datetime.now()
    await db.commit()
    
    return user

async def update_user(db: AsyncSession, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
    """Update user"""
    query = update(User).where(User.id == user_id).values(**update_data).returning(User)
    result = await db.execute(query)
    await db.commit()
    return result.scalar_one_or_none()

async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete user"""
    query = delete(User).where(User.id == user_id)
    result = await db.execute(query)
    await db.commit()
    return result.rowcount > 0

# Ticket CRUD operations
async def create_ticket(db: AsyncSession, ticket_data: Dict[str, Any]) -> Ticket:
    """Create a new ticket"""
    ticket = Ticket(**ticket_data)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket

async def get_ticket_by_id(db: AsyncSession, ticket_id: int) -> Optional[Ticket]:
    """Get ticket by ID"""
    query = select(Ticket).where(Ticket.id == ticket_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_tickets(
    db: AsyncSession,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Ticket]:
    """Get tickets with filters"""
    query = select(Ticket)
    
    if user_id:
        query = query.where(
            or_(Ticket.created_by == user_id, Ticket.assigned_to == user_id)
        )
    
    if status:
        query = query.where(Ticket.status == status)
    
    if priority:
        query = query.where(Ticket.priority == priority)
    
    query = query.offset(skip).limit(limit).order_by(Ticket.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def update_ticket(db: AsyncSession, ticket_id: int, update_data: Dict[str, Any]) -> Optional[Ticket]:
    """Update ticket"""
    query = update(Ticket).where(Ticket.id == ticket_id).values(**update_data).returning(Ticket)
    result = await db.execute(query)
    await db.commit()
    return result.scalar_one_or_none()

async def delete_ticket(db: AsyncSession, ticket_id: int) -> bool:
    """Delete ticket"""
    query = delete(Ticket).where(Ticket.id == ticket_id)
    result = await db.execute(query)
    await db.commit()
    return result.rowcount > 0

# Document CRUD operations
async def create_document(db: AsyncSession, document_data: Dict[str, Any]) -> Document:
    """Create a new document"""
    document = Document(**document_data)
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document

async def get_document_by_id(db: AsyncSession, document_id: int) -> Optional[Document]:
    """Get document by ID"""
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_documents(
    db: AsyncSession,
    user_id: Optional[int] = None,
    processed: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Document]:
    """Get documents with filters"""
    query = select(Document)
    
    if user_id:
        query = query.where(Document.uploaded_by == user_id)
    
    if processed is not None:
        query = query.where(Document.processed == processed)
    
    query = query.offset(skip).limit(limit).order_by(Document.uploaded_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def update_document(db: AsyncSession, document_id: int, update_data: Dict[str, Any]) -> Optional[Document]:
    """Update document"""
    query = update(Document).where(Document.id == document_id).values(**update_data).returning(Document)
    result = await db.execute(query)
    await db.commit()
    return result.scalar_one_or_none()

async def delete_document(db: AsyncSession, document_id: int) -> bool:
    """Delete document"""
    query = delete(Document).where(Document.id == document_id)
    result = await db.execute(query)
    await db.commit()
    return result.rowcount > 0

# Message CRUD operations
async def create_message(db: AsyncSession, message_data: Dict[str, Any]) -> Message:
    """Create a new message"""
    message = Message(**message_data)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message

async def get_messages_by_conversation(
    db: AsyncSession,
    conversation_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[Message]:
    """Get messages by conversation ID"""
    query = select(Message).where(
        Message.conversation_id == conversation_id
    ).offset(skip).limit(limit).order_by(Message.created_at)
    
    result = await db.execute(query)
    return result.scalars().all()

async def get_conversation_messages(db: AsyncSession, conversation_id: str) -> List[Message]:
    """Get all messages in a conversation"""
    return await get_messages_by_conversation(db, conversation_id, limit=1000)

# Conversation CRUD operations
async def create_conversation(db: AsyncSession, conversation_data: Dict[str, Any]) -> Conversation:
    """Create a new conversation"""
    conversation = Conversation(**conversation_data)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation

async def get_conversation_by_id(db: AsyncSession, conversation_id: str) -> Optional[Conversation]:
    """Get conversation by ID"""
    query = select(Conversation).where(Conversation.conversation_id == conversation_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_user_conversations(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[Conversation]:
    """Get user's conversations"""
    query = select(Conversation).where(
        Conversation.user_id == user_id
    ).offset(skip).limit(limit).order_by(Conversation.updated_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()

async def update_conversation(
    db: AsyncSession,
    conversation_id: str,
    update_data: Dict[str, Any]
) -> Optional[Conversation]:
    """Update conversation"""
    query = update(Conversation).where(
        Conversation.conversation_id == conversation_id
    ).values(**update_data).returning(Conversation)
    
    result = await db.execute(query)
    await db.commit()
    return result.scalar_one_or_none()

# Audit Log CRUD operations
async def create_audit_log(db: AsyncSession, log_data: Dict[str, Any]) -> AuditLog:
    """Create an audit log entry"""
    log = AuditLog(**log_data)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log

async def get_audit_logs(
    db: AsyncSession,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> List[AuditLog]:
    """Get audit logs with filters"""
    query = select(AuditLog)
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    
    if action:
        query = query.where(AuditLog.action == action)
    
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

# Analytics and statistics
async def get_ticket_statistics(db: AsyncSession, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Get ticket statistics"""
    try:
        # Base query
        query = select(Ticket)
        if user_id:
            query = query.where(or_(Ticket.created_by == user_id, Ticket.assigned_to == user_id))
        
        # Get all tickets
        result = await db.execute(query)
        tickets = result.scalars().all()
        
        # Calculate statistics
        total = len(tickets)
        open_count = sum(1 for t in tickets if t.status == TicketStatus.OPEN)
        in_progress = sum(1 for t in tickets if t.status == TicketStatus.IN_PROGRESS)
        resolved = sum(1 for t in tickets if t.status == TicketStatus.RESOLVED)
        closed = sum(1 for t in tickets if t.status == TicketStatus.CLOSED)
        
        # Priority distribution
        priority_counts = {}
        for priority in TicketPriority:
            count = sum(1 for t in tickets if t.priority == priority)
            if count > 0:
                priority_counts[priority.value] = count
        
        return {
            'total': total,
            'open': open_count,
            'in_progress': in_progress,
            'resolved': resolved,
            'closed': closed,
            'priority_distribution': priority_counts,
            'resolution_rate': round((resolved + closed) / total * 100, 2) if total > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Error getting ticket statistics: {str(e)}")
        return {}