from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request
import json
from app.database import crud
from app.utils.logger import logger
from app.config import settings

class AuditLogger:
    """Audit logging service"""
    
    @staticmethod
    async def log_event(
        db: AsyncSession,
        user_id: Optional[int],
        action: str,
        details: Any,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        request: Optional[Request] = None
    ) -> None:
        """Log an audit event"""
        try:
            if not settings.AUDIT_LOG_ENABLED:
                return
            
            ip_address = None
            user_agent = None
            
            if request:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
            
            if not isinstance(details, dict):
                details = {"message": str(details)}
            
            details["timestamp"] = datetime.now().isoformat()
            
            log_data = {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            
            await crud.create_audit_log(db, log_data)
            
            logger.info(
                f"AUDIT: user={user_id}, action={action}, "
                f"resource={resource_type}:{resource_id}, details={json.dumps(details)}"
            )
        
        except Exception as e:
            logger.error(f"Error logging audit event: {str(e)}")
    
    @staticmethod
    async def log_security_event(
        db: AsyncSession,
        user_id: Optional[int],
        event_type: str,
        details: Any,
        request: Optional[Request] = None,
        severity: str = "medium"
    ) -> None:
        if not isinstance(details, dict):
            details = {"message": str(details)}
        
        details["severity"] = severity
        details["event_type"] = event_type
        
        await AuditLogger.log_event(
            db=db,
            user_id=user_id,
            action=f"security_{event_type}",
            details=details,
            resource_type="security",
            request=request
        )
    
    @staticmethod
    async def log_access_event(
        db: AsyncSession,
        user_id: Optional[int],
        resource_type: str,
        resource_id: int,
        access_type: str,
        request: Optional[Request] = None
    ) -> None:
        await AuditLogger.log_event(
            db=db,
            user_id=user_id,
            action=f"access_{access_type}",
            details={
                "access_type": access_type,
                "resource_type": resource_type,
                "resource_id": resource_id
            },
            resource_type=resource_type,
            resource_id=resource_id,
            request=request
        )
    
    @staticmethod
    async def log_authentication_event(
        db: AsyncSession,
        username: str,
        success: bool,
        request: Optional[Request] = None
    ) -> None:
        await AuditLogger.log_security_event(
            db=db,
            user_id=None,
            event_type="authentication",
            details={
                "username": username,
                "success": success,
                "attempt_time": datetime.now().isoformat()
            },
            request=request,
            severity="high" if not success else "low"
        )

# ===== Convenience functions =====
async def log_audit_event(
    db: AsyncSession,
    user_id: Optional[int],
    action: str,
    details: Any,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    request: Optional[Request] = None
) -> None:
    await AuditLogger.log_event(
        db=db,
        user_id=user_id,
        action=action,
        details=details,
        resource_type=resource_type,
        resource_id=resource_id,
        request=request
    )

async def log_security_event(
    db: AsyncSession,
    user_id: Optional[int],
    event_type: str,
    details: Any,
    request: Optional[Request] = None,
    severity: str = "medium"
) -> None:
    await AuditLogger.log_security_event(
        db=db,
        user_id=user_id,
        event_type=event_type,
        details=details,
        request=request,
        severity=severity
    )

async def log_access_event(
    db: AsyncSession,
    user_id: Optional[int],
    resource_type: str,
    resource_id: int,
    access_type: str,
    request: Optional[Request] = None
) -> None:
    await AuditLogger.log_access_event(
        db=db,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        access_type=access_type,
        request=request
    )

async def log_authentication_event(
    db: AsyncSession,
    username: str,
    success: bool,
    request: Optional[Request] = None
) -> None:
    await AuditLogger.log_authentication_event(
        db=db,
        username=username,
        success=success,
        request=request
    )
