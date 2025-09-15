from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import secrets

from app.database.connection import get_db_session
from app.database.models import User, RefreshToken, UserRole
from app.auth.security import verify_token


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    # Fix: Safely extract user_id with type checking
    user_id_raw = payload.get("sub")
    if user_id_raw is None or not isinstance(user_id_raw, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = user_id_raw
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fix: Safe access to user.is_active SQLAlchemy column
    is_active = getattr(user, 'is_active', False)
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    # Fix: Safe access to current_user.is_active SQLAlchemy column
    is_active = getattr(current_user, 'is_active', False)
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def generate_state() -> str:
    """Generate a random state for OAuth flow."""
    return secrets.token_urlsafe(32)


async def validate_refresh_token(
    refresh_token: str,
    db: AsyncSession
) -> Optional[User]:
    """Validate refresh token and return associated user."""
    try:
        payload = verify_token(refresh_token, "refresh")
        token_id = payload.get("jti")
        
        if not token_id:
            return None
        
        result = await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token == refresh_token)
            .where(RefreshToken.is_revoked == False)
        )
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            return None
        
        # Get associated user
        result = await db.execute(select(User).where(User.id == db_token.user_id))
        user = result.scalar_one_or_none()
        
        # Fix: Safe access to user.is_active if user exists
        if user:
            is_active = getattr(user, 'is_active', False)
            return user if is_active else None
        return None
        
    except Exception:
        return None


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current authenticated admin user."""
    # Fix: Safe access to current_user.role SQLAlchemy column
    user_role = getattr(current_user, 'role', None)
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Fix: Safe access to current_user.role SQLAlchemy column
        user_role = getattr(current_user, 'role', None)
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' required"
            )
        return current_user
    return role_checker


# Pre-defined role dependencies
require_admin = require_role(UserRole.ADMIN)
require_user = require_role(UserRole.USER)