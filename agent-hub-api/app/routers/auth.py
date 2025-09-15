from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
import logging

from app.database.connection import get_db_session
from app.services.auth_service import AuthService
from app.auth.dependencies import get_current_user, get_current_admin_user, generate_state
from app.models.schemas import Token, TokenRefresh, GitHubAuthResponse, UserResponse, UserLogin, UserSignup, UserCreateAdmin, UserUpdate, UserRole
from app.database.models import User
from app.config.settings import FRONTEND_URL
from app.utils.activity_logger import ActivityLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()

@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db_session)
):
    """Authenticate user with email and password."""
    tokens = await auth_service.authenticate_with_credentials(
        db, user_credentials.email, user_credentials.password
    )
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Log user login event
    activity_logger = ActivityLogger(db)
    user = await auth_service.get_user_by_email(db, user_credentials.email)
    if user:
        await activity_logger.log_user_event(
            f"User logged in: {user.email}",
            user_id=str(user.id)
        )
    
    return tokens


@router.post("/signup", response_model=Token)
async def signup(
    user_data: UserSignup,
    db: AsyncSession = Depends(get_db_session)
):
    """Register a new user with email and password."""
    try:
        tokens = await auth_service.create_user_with_credentials(
            db, user_data.full_name, user_data.email, user_data.password
        )
        
        # Log user registration event
        activity_logger = ActivityLogger(db)
        user = await auth_service.get_user_by_email(db, user_data.email)
        if user:
            await activity_logger.log_user_event(
                f"New user registered: {user.email}",
                user_id=str(user.id)
            )
        
        return tokens
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )


@router.get("/github/login", response_model=GitHubAuthResponse)
async def github_login():
    """Initiate GitHub OAuth login."""
    state = generate_state()
    authorization_url = auth_service.get_github_authorization_url(state)
    
    return GitHubAuthResponse(
        authorization_url=authorization_url,
        state=state
    )


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Handle GitHub OAuth callback."""
    # Use configured frontend URL
    frontend_url = FRONTEND_URL
    
    if error:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error={error}",
            status_code=status.HTTP_302_FOUND
        )
    
    if not code:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error=missing_code",
            status_code=status.HTTP_302_FOUND
        )
    
    try:
        # Authenticate with GitHub and create tokens
        tokens = await auth_service.authenticate_with_github(db, code)
        
        # Log GitHub login event
        activity_logger = ActivityLogger(db)
        # Get user info to log the event
        try:
            # Create a mock credentials object to pass to get_current_user
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=tokens.access_token)
            user = await get_current_user(credentials, db)
            if user:
                await activity_logger.log_user_event(
                    f"User logged in via GitHub: {user.email}",
                    user_id=str(user.id)
                )
        except Exception as e:
            # If we can't get the user from the token, log without user details
            logger.warning(f"Could not get user from token for logging: {e}")
        
        # Redirect to frontend with tokens as URL parameters
        # Note: This is less secure but works with localStorage approach
        # In production, consider using secure cookies or a different flow
        redirect_url = (
            f"{frontend_url}/auth/callback"
            f"?success=true"
            f"&access_token={tokens.access_token}"
            f"&refresh_token={tokens.refresh_token}"
            f"&token_type={tokens.token_type}"
            f"&expires_in={tokens.expires_in}"
        )
        if state:
            redirect_url += f"&state={state}"
        
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db_session)
):
    """Refresh access token using refresh token."""
    tokens = await auth_service.refresh_token(db, token_data.refresh_token)
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    return tokens


@router.post("/logout")
async def logout(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db_session)
):
    """Logout user by revoking refresh token."""
    success = await auth_service.revoke_refresh_token(db, token_data.refresh_token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout"
        )
    
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Logout user from all devices by revoking all refresh tokens."""
    # Fix: Convert current_user.id to string to avoid SQLAlchemy type issues
    user_id = str(getattr(current_user, 'id', ''))
    success = await auth_service.revoke_all_user_tokens(db, user_id)
    
    return {"message": f"Successfully logged out from all devices"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse.from_orm(current_user)


@router.delete("/me")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete current user account."""
    # Fix: Convert current_user.id to string to avoid SQLAlchemy type issues
    user_id = str(getattr(current_user, 'id', ''))
    
    # Revoke all tokens first
    await auth_service.revoke_all_user_tokens(db, user_id)
    
    # In a real application, you might want to soft delete or
    # move data to an archive before deletion
    # For now, we'll just deactivate the account
    await auth_service.update_user(db, user_id, {"is_active": False})
    
    # Log user deletion event
    activity_logger = ActivityLogger(db)
    await activity_logger.log_user_event(
        f"User account deleted: user ID {user_id}",
        user_id=user_id
    )
    
    return {"message": "Account deactivated successfully"}


# Admin endpoints
@router.post("/admin/users", response_model=UserResponse)
async def create_user_admin(
    user_data: UserCreateAdmin,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new user (admin only)."""
    try:
        # Fix: Import database UserRole for proper type conversion
        from app.database.models import UserRole as ModelUserRole
        
        if user_data.password:
            # Convert schema UserRole to database UserRole
            db_role = None
            if user_data.role:
                db_role = ModelUserRole.ADMIN if user_data.role.value.upper() == "ADMIN" else ModelUserRole.USER
            
            tokens = await auth_service.create_user_with_credentials(
                db, user_data.full_name, user_data.email, user_data.password, db_role
            )
            # Get the created user to return
            user = await auth_service.get_user_by_email(db, user_data.email)
            
            # Log user creation event
            activity_logger = ActivityLogger(db)
            if user:
                await activity_logger.log_user_event(
                    f"Admin created new user: {user.email}",
                    user_id=str(current_user.id)
                )
            
            return UserResponse.from_orm(user)
        else:
            # Create OAuth user without password
            # Convert schema UserRole to database UserRole
            db_role = None
            if user_data.role:
                db_role = ModelUserRole.ADMIN if user_data.role.value.upper() == "ADMIN" else ModelUserRole.USER
            
            user_dict = {
                "username": user_data.username,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "role": db_role
            }
            user = await auth_service.create_user(db, user_dict)
            
            # Log user creation event
            activity_logger = ActivityLogger(db)
            await activity_logger.log_user_event(
                f"Admin created new OAuth user: {user.email}",
                user_id=str(current_user.id)
            )
            
            return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/admin/users", response_model=list[UserResponse])
async def list_users(
    role: Optional[UserRole] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all users or users by role (admin only)."""
    if role:
        # Fix: Convert schema UserRole to database UserRole
        from app.database.models import UserRole as ModelUserRole
        db_role = ModelUserRole.ADMIN if role.value.upper() == "ADMIN" else ModelUserRole.USER
        users = await auth_service.get_users_by_role(db, db_role)
    else:
        # Get all users
        from sqlalchemy import select
        result = await db.execute(select(User))
        # Fix: Convert SQLAlchemy Sequence to Python list
        users = list(result.scalars().all())
    
    return [UserResponse.from_orm(user) for user in users]


@router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update user role (admin only)."""
    user = await auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Fix: Convert current_user.id to string for comparison
    current_user_id = str(getattr(current_user, 'id', ''))
    current_user_role = getattr(current_user, 'role', None)
    
    # Fix: Import UserRole from the models module to ensure correct enum type
    from app.database.models import UserRole as ModelUserRole
    
    # Convert schema UserRole to database UserRole
    db_new_role = ModelUserRole.ADMIN if new_role.value.upper() == "ADMIN" else ModelUserRole.USER
    
    # Prevent self-demotion of the last admin
    if current_user_id == user_id and current_user_role == ModelUserRole.ADMIN and db_new_role != ModelUserRole.ADMIN:
        admin_count = len(await auth_service.get_users_by_role(db, ModelUserRole.ADMIN))
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last admin user"
            )
    
    updated_user = await auth_service.update_user(db, user_id, {"role": db_new_role})
    
    # Log role change event
    activity_logger = ActivityLogger(db)
    await activity_logger.log_user_event(
        f"User role changed from {user.role.value} to {new_role.value} for user ID {user_id}",
        user_id=str(current_user.id),
        metadata={"target_user_id": user_id, "new_role": new_role.value}
    )
    
    return {"message": f"User role updated to {new_role.value}", "user": UserResponse.from_orm(updated_user)}


@router.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user_admin(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get user details (admin only)."""
    user = await auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.from_orm(user)


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update user details (admin only)."""
    user = await auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Fix: Convert current_user attributes to Python values
    current_user_id = str(getattr(current_user, 'id', ''))
    current_user_role = getattr(current_user, 'role', None)
    
    # Fix: Import ModelUserRole for database operations
    from app.database.models import UserRole as ModelUserRole
    
    # Convert schema UserRole to database UserRole if provided
    db_role = None
    if user_data.role:
        db_role = ModelUserRole.ADMIN if user_data.role.value.upper() == "ADMIN" else ModelUserRole.USER
    
    # Prevent self-role change if demoting the last admin
    if current_user_id == user_id and db_role and current_user_role == ModelUserRole.ADMIN and db_role != ModelUserRole.ADMIN:
        admin_count = len(await auth_service.get_users_by_role(db, ModelUserRole.ADMIN))
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last admin user"
            )
    
    # Prevent self-deactivation if user is the last admin
    if current_user_id == user_id and user_data.is_active is False and current_user_role == ModelUserRole.ADMIN:
        admin_count = len(await auth_service.get_users_by_role(db, ModelUserRole.ADMIN))
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last admin user"
            )
    
    # Build update data dictionary
    update_data = {}
    if user_data.full_name is not None:
        update_data["full_name"] = user_data.full_name
    if user_data.email is not None:
        update_data["email"] = user_data.email
    if db_role is not None:  # Use converted database role
        update_data["role"] = db_role
    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active
    
    try:
        updated_user = await auth_service.update_user(db, user_id, update_data)
        
        # Log user update event
        activity_logger = ActivityLogger(db)
        await activity_logger.log_user_event(
            f"Admin updated user profile information for user ID {user_id}",
            user_id=str(current_user.id),
            metadata={"target_user_id": user_id, "updated_fields": list(update_data.keys())}
        )
        
        return UserResponse.from_orm(updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/admin/users/{user_id}")
async def delete_user_admin(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete user (admin only)."""
    user = await auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Fix: Convert current_user.id to string for comparison
    current_user_id = str(getattr(current_user, 'id', ''))
    
    # Prevent self-deletion
    if current_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Fix: Safe access to user.role
    user_role = getattr(user, 'role', None)
    
    # Fix: Import ModelUserRole for database operations
    from app.database.models import UserRole as ModelUserRole
    
    # Prevent deletion of the last admin
    if user_role == ModelUserRole.ADMIN:
        admin_count = len(await auth_service.get_users_by_role(db, ModelUserRole.ADMIN))
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin user"
            )
    
    # Revoke all user's tokens first
    await auth_service.revoke_all_user_tokens(db, user_id)
    
    # Delete the user (this will cascade delete related data due to relationship constraints)
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(User).where(User.id == user_id))
    await db.commit()
    
    # Log user deletion event
    activity_logger = ActivityLogger(db)
    await activity_logger.log_user_event(
        f"Admin deleted user account: user ID {user_id}",
        user_id=str(current_user.id),
        metadata={"deleted_user_id": user_id}
    )
    
    return {"message": "User deleted successfully"}