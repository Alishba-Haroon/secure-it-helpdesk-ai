from functools import wraps
from typing import List, Callable, Any
from fastapi import HTTPException, status
from app.database.models import UserRole
from app.utils.logger import logger

class PermissionChecker:
    """Permission checking utility"""
    
    # Role-based permissions
    ROLE_PERMISSIONS = {
        UserRole.USER: [
            "ticket:create",
            "ticket:view:own",
            "ticket:update:own",
            "message:create",
            "document:view:own",
            "document:upload:own",
            "conversation:create",
            "conversation:view:own"
        ],
        UserRole.AGENT: [
            "ticket:create",
            "ticket:view:all",
            "ticket:update:all",
            "ticket:assign",
            "ticket:resolve",
            "message:create",
            "message:view:all",
            "document:view:all",
            "document:upload:own",
            "document:process",
            "conversation:create",
            "conversation:view:all",
            "user:view:basic"
        ],
        UserRole.ADMIN: [
            "ticket:*",
            "message:*",
            "document:*",
            "conversation:*",
            "user:view:all",
            "user:create",
            "user:update",
            "user:delete",
            "system:configure",
            "audit:view",
            "knowledge:manage"
        ],
        UserRole.SUPER_ADMIN: [
            "*"
        ]
    }
    
    @classmethod
    def has_permission(cls, user_role: str, permission: str) -> bool:
        """Check if a user role has a specific permission"""
        if user_role == UserRole.SUPER_ADMIN:
            return True
        
        user_permissions = cls.ROLE_PERMISSIONS.get(user_role, [])
        
        # Check for wildcard permissions
        if "*" in user_permissions:
            return True
        
        # Check for exact match
        if permission in user_permissions:
            return True
        
        # Check for wildcard patterns (e.g., "ticket:*")
        for user_perm in user_permissions:
            if user_perm.endswith("*") and permission.startswith(user_perm[:-1]):
                return True
        
        return False
    
    @classmethod
    def require_permission(cls, permission: str):
        """Decorator to require a specific permission"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Get current_user from kwargs or args
                current_user = None
                if 'current_user' in kwargs:
                    current_user = kwargs['current_user']
                elif len(args) > 0:
                    # Check if first arg is current_user
                    if hasattr(args[0], 'role'):
                        current_user = args[0]
                
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                if not cls.has_permission(current_user.role, permission):
                    logger.warning(
                        f"Permission denied for user {current_user.username} "
                        f"(role: {current_user.role}) on permission: {permission}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

# Convenience permission functions
def require_permission(permission: str):
    """Require a permission for a function"""
    return PermissionChecker.require_permission(permission)

def require_roles(roles: List[str]):
    """Require one of the specified roles"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = None
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            elif len(args) > 0 and hasattr(args[0], 'role'):
                current_user = args[0]
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if current_user.role not in roles:
                logger.warning(
                    f"Role access denied for user {current_user.username} "
                    f"(role: {current_user.role}) on required roles: {roles}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_ownership(resource_getter: Callable):
    """Check if user owns the resource"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = None
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            elif len(args) > 0 and hasattr(args[0], 'role'):
                current_user = args[0]
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get the resource
            resource = await resource_getter(*args, **kwargs)
            if not resource:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resource not found"
                )
            
            # Check if user owns the resource or has admin/super admin role
            if current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                return await func(*args, **kwargs)
            
            # Get user_id from resource
            user_id = getattr(resource, 'user_id', None) or getattr(resource, 'created_by', None)
            if user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access this resource"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Resource-specific permission checks
async def can_modify_ticket(db, ticket_id: int, user_id: int) -> bool:
    """Check if user can modify a ticket"""
    from app.database import crud
    ticket = await crud.get_ticket_by_id(db, ticket_id)
    
    if not ticket:
        return False
    
    # Admin/SuperAdmin can modify any ticket
    user = await crud.get_user_by_id(db, user_id)
    if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        return True
    
    # User can modify their own tickets
    if ticket.created_by == user_id:
        return True
    
    # Agent can modify assigned tickets
    if user.role == UserRole.AGENT and ticket.assigned_to == user_id:
        return True
    
    return False

async def can_view_document(db, document_id: int, user_id: int) -> bool:
    """Check if user can view a document"""
    from app.database import crud
    document = await crud.get_document_by_id(db, document_id)
    
    if not document:
        return False
    
    # Admin/SuperAdmin can view any document
    user = await crud.get_user_by_id(db, user_id)
    if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        return True
    
    # User can view their own documents
    if document.uploaded_by == user_id:
        return True
    
    # Agents can view all documents
    if user.role == UserRole.AGENT:
        return True
    
    return False