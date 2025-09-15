from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any
import uuid

from app.database.models import User, RefreshToken, UserRole, Agent, AgentOwnership
from app.database.models import User, RefreshToken, UserRole, Agent, AgentOwnership
from app.auth.security import (
    create_access_token, 
    create_refresh_token, 
    get_password_hash, 
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from app.auth.github_oauth import GitHubOAuth
from app.models.schemas import UserCreate, UserResponse, Token
from app.services.agent_sync_service import AgentSyncService
from app.utils.activity_logger import ActivityLogger


class AuthService:
    def __init__(self):
        self.github_oauth = GitHubOAuth()
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return get_password_hash(password)
    
    def verify_user_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return verify_password(password, hashed_password)
    
    async def _create_refresh_token(self, db: AsyncSession, user_id: str) -> RefreshToken:
        """Create a new refresh token for a user."""
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user_id, "jti": str(uuid.uuid4())},
            expires_delta=refresh_token_expires
        )
        
        db_refresh_token = RefreshToken(
            user_id=user_id,
            token=refresh_token,
            expires_at=datetime.utcnow() + refresh_token_expires
        )
        
        db.add(db_refresh_token)
        await db.commit()
        await db.refresh(db_refresh_token)
        return db_refresh_token

    async def _assign_sample_agent_to_user(self, db: AsyncSession, user_id: str) -> None:
        """Automatically assign the Sample Agent to a newly created user."""
        try:
            # Get the Sample Agent by name
            sample_agent_dict = await AgentSyncService.get_agent_by_name(db, "sample_agent")
            
            # If the Sample Agent exists, create an ownership record
            if sample_agent_dict:
                # Check if the ownership already exists (shouldn't happen for new users, but just in case)
                result = await db.execute(
                    select(AgentOwnership).where(
                        and_(
                            AgentOwnership.user_id == user_id,
                            AgentOwnership.agent_id == sample_agent_dict["id"]
                        )
                    )
                )
                existing_ownership = result.scalar_one_or_none()
                
                if not existing_ownership:
                    # Create the ownership record
                    ownership = AgentOwnership(
                        user_id=user_id,
                        agent_id=sample_agent_dict["id"]
                    )
                    db.add(ownership)
                    await db.commit()
        except Exception as e:
            # Log the error but don't fail user creation
            print(f"Warning: Failed to automatically assign Sample Agent to user {user_id}: {e}")
            await db.rollback()

    async def create_user(
        self, 
        db: AsyncSession, 
        user_data: Dict[str, Any],
        github_token: Optional[str] = None
    ) -> User:
        """Create a new user."""
        user = User(
            username=user_data.get("username"),
            email=user_data.get("email"),
            full_name=user_data.get("full_name"),
            role=user_data.get("role", UserRole.USER),  # Default to USER role
            github_id=user_data.get("github_id"),
            avatar_url=user_data.get("avatar_url"),
            github_token=github_token,  # Store encrypted in production
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Automatically assign the Sample Agent to the new user
        user_id_str = str(user.id)
        await self._assign_sample_agent_to_user(db, user_id_str)
        
        return user

    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_github_id(self, db: AsyncSession, github_id: str) -> Optional[User]:
        """Get user by GitHub ID."""
        result = await db.execute(select(User).where(User.github_id == github_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def update_user(
        self, 
        db: AsyncSession, 
        user_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[User]:
        """Update user information."""
        from app.database.models import UserRole as ModelUserRole
        from app.models.schemas import UserRole as SchemaUserRole
        
        # Check if email is being updated and if it already exists
        if "email" in update_data:
            existing_user = await self.get_user_by_email(db, update_data["email"])
            if existing_user:
                # Fix: Convert existing_user.id to string to avoid SQLAlchemy type issues
                existing_user_id = str(getattr(existing_user, 'id', ''))
                if existing_user_id != user_id:
                    raise ValueError("User with this email already exists")
        
        # Convert role if present
        if "role" in update_data:
            role_value = update_data["role"]
            if isinstance(role_value, str):
                # Handle string role values
                update_data["role"] = ModelUserRole.USER if role_value.lower() == "user" else ModelUserRole.ADMIN
            elif hasattr(role_value, 'value'):
                # Handle enum values
                update_data["role"] = ModelUserRole.USER if role_value.value.lower() == "user" else ModelUserRole.ADMIN
        
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        await db.commit()
        return await self.get_user_by_id(db, user_id)

    async def create_tokens(self, db: AsyncSession, user: User) -> Token:
        """Create access and refresh tokens for user."""
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id, "username": user.username},
            expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": user.id, "jti": str(uuid.uuid4())},
            expires_delta=refresh_token_expires
        )

        # Store refresh token in database
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=datetime.utcnow() + refresh_token_expires
        )
        db.add(db_refresh_token)
        await db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    async def refresh_token(self, db: AsyncSession, refresh_token: str) -> Optional[Token]:
        """Refresh access token using refresh token."""
        from app.auth.dependencies import validate_refresh_token
        
        user = await validate_refresh_token(refresh_token, db)
        if not user:
            return None

        # Revoke old refresh token
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token == refresh_token)
            .values(is_revoked=True)
        )

        # Create new tokens
        return await self.create_tokens(db, user)

    async def revoke_refresh_token(self, db: AsyncSession, refresh_token: str) -> bool:
        """Revoke a refresh token."""
        result = await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token == refresh_token)
            .values(is_revoked=True)
        )
        await db.commit()
        return result.rowcount > 0

    async def revoke_all_user_tokens(self, db: AsyncSession, user_id: str) -> bool:
        """Revoke all refresh tokens for a user."""
        result = await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(is_revoked=True)
        )
        await db.commit()
        return result.rowcount > 0

    async def cleanup_expired_tokens(self, db: AsyncSession) -> int:
        """Clean up expired refresh tokens."""
        result = await db.execute(
            delete(RefreshToken)
            .where(RefreshToken.expires_at < datetime.utcnow())
        )
        await db.commit()
        return result.rowcount

    # GitHub OAuth methods
    def get_github_authorization_url(self, state: Optional[str] = None) -> str:
        """Get GitHub OAuth authorization URL."""
        return self.github_oauth.get_authorization_url(state)

    async def authenticate_with_github(
        self, 
        db: AsyncSession, 
        code: str
    ) -> Token:
        """Authenticate user with GitHub OAuth."""
        # Exchange code for token
        token_data = await self.github_oauth.exchange_code_for_token(code)
        github_access_token = token_data.get("access_token")
        
        if not github_access_token:
            raise ValueError("Failed to get GitHub access token")

        # Get user info from GitHub
        github_user = await self.github_oauth.get_user_info(github_access_token)
        
        # Check if user already exists
        existing_user = await self.get_user_by_github_id(db, github_user["github_id"])
        
        if existing_user:
            # Fix: Convert existing_user.id to string to avoid SQLAlchemy type issues
            user_id = str(getattr(existing_user, 'id', ''))
            # Update user's GitHub token
            await self.update_user(
                db, 
                user_id,  # Use converted string ID
                {"github_token": github_access_token}
            )
            user = existing_user
        else:
            # Check if user exists with same email
            existing_email_user = await self.get_user_by_email(db, github_user["email"])
            if existing_email_user:
                # Fix: Convert existing_email_user.id to string to avoid SQLAlchemy type issues
                email_user_id = str(getattr(existing_email_user, 'id', ''))
                # Link GitHub account to existing user
                await self.update_user(
                    db,
                    email_user_id,  # Use converted string ID
                    {
                        "github_id": github_user["github_id"],
                        "github_token": github_access_token,
                        "avatar_url": github_user.get("avatar_url")
                    }
                )
                user = existing_email_user
            else:
                # Create new user
                user = await self.create_user(db, github_user, github_access_token)

        # Create and return tokens
        return await self.create_tokens(db, user)

    async def authenticate_with_credentials(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[Token]:
        """Authenticate user with email and password."""
        # Get user by email
        user = await self.get_user_by_email(db, email)
        
        if not user:
            return None
        
        # Fix: Check if user has password (not OAuth-only user) - safe access to password_hash
        password_hash = getattr(user, 'password_hash', None)
        if not password_hash:
            return None
            
        # Verify password
        if not verify_password(password, password_hash):
            return None
            
        # Fix: Check if user is active - safe access to is_active
        is_active = getattr(user, 'is_active', False)
        if not is_active:
            return None
            
        # Create and return tokens
        return await self.create_tokens(db, user)

    async def create_user_with_credentials(
        self,
        db: AsyncSession,
        full_name: str,
        email: str,
        password: str,
        role: Optional["UserRole"] = None
    ) -> Token:
        """Create a new user with email/password credentials."""
        from app.models.schemas import UserRole as SchemaUserRole
        from app.database.models import UserRole as ModelUserRole
        
        # Check if user already exists
        existing_user = await self.get_user_by_email(db, email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        password_hash = self.hash_password(password)
        
        # Generate username from email if not provided
        username = email.split("@")[0]
        
        # Ensure unique username
        base_username = username
        counter = 1
        while await self.get_user_by_username(db, username):
            username = f"{base_username}{counter}"
            counter += 1
        
        # Convert schema role to model role
        if role is None:
            user_role = ModelUserRole.USER
        elif isinstance(role, str):
            # Handle string role values
            user_role = ModelUserRole.USER if role.lower() == "user" else ModelUserRole.ADMIN
        else:
            # Handle enum values - convert to model enum
            user_role = ModelUserRole.USER if role == SchemaUserRole.USER else ModelUserRole.ADMIN
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=user_role,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Automatically assign the Sample Agent to the new user
        user_id_str = str(user.id)
        await self._assign_sample_agent_to_user(db, user_id_str)
        
        # Generate tokens using the existing method
        return await self.create_tokens(db, user)
    
    # Role-based helper methods
    async def is_admin(self, user: User) -> bool:
        """Check if user has admin role."""
        # Fix: Safe access to user.role to avoid SQLAlchemy type issues
        user_role = getattr(user, 'role', None)
        return user_role == UserRole.ADMIN
    
    async def promote_user_to_admin(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Promote a user to admin role."""
        return await self.update_user(db, user_id, {"role": UserRole.ADMIN})
    
    async def demote_admin_to_user(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Demote an admin to user role."""
        return await self.update_user(db, user_id, {"role": UserRole.USER})
    
    async def create_admin_user(
        self,
        db: AsyncSession,
        full_name: str,
        email: str,
        password: str
    ) -> User:
        """Create an admin user without generating tokens (for admin creation script)."""
        # Check if user already exists
        existing_user = await self.get_user_by_email(db, email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        password_hash = self.hash_password(password)
        
        # Generate username from email if not provided
        username = email.split("@")[0]
        
        # Ensure unique username
        base_username = username
        counter = 1
        while await self.get_user_by_username(db, username):
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=UserRole.ADMIN,  # Always admin for this method
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Automatically assign the Sample Agent to the new admin user
        user_id_str = str(user.id)
        await self._assign_sample_agent_to_user(db, user_id_str)
        
        return user

    async def get_users_by_role(self, db: AsyncSession, role: UserRole) -> list[User]:
        """Get all users with a specific role."""
        result = await db.execute(select(User).where(User.role == role))
        # Fix: Convert SQLAlchemy Sequence to Python list
        return list(result.scalars().all())
