from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# User Role Enum
class UserRole(str, Enum):
    """User role enumeration for role-based access control."""
    ADMIN = "admin"
    USER = "user"


# Activity Log Enums
class ActivityLogType(str, Enum):
    USER = "USER"
    CHAT = "CHAT"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


class ActivityLogSeverity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Auth Models
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    role: Optional[UserRole] = UserRole.USER


class UserCreate(UserBase):
    password: Optional[str] = None  # For non-OAuth registration


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    github_id: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserSignup(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class UserCreateAdmin(BaseModel):
    """Schema for creating users with role assignment (admin only)."""
    full_name: str
    email: EmailStr
    username: str
    password: Optional[str] = None
    role: UserRole = UserRole.USER


class GitHubAuthResponse(BaseModel):
    authorization_url: str
    state: str


# Chat Models
class QueryRequest(BaseModel):
    message: str
    files: Optional[List[str]] = []  # File names/IDs
    selected_agents: Optional[List[str]] = []


class QueryResponse(BaseModel):
    id: str
    chat_id: str
    message: str
    response: Optional[str] = None
    agent_used: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    files_uploaded: Optional[List[Dict[str, Any]]] = None
    selected_agents: Optional[List[str]] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    queries: List[QueryResponse] = []

    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    title: Optional[str] = None
    message: str  # First message
    files: Optional[List[str]] = []
    selected_agents: Optional[List[str]] = []


class ChatUpdate(BaseModel):
    title: Optional[str] = None


class ChatListResponse(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_queries: int

    class Config:
        from_attributes = True


# Activity Log Models
class ActivityLogCreate(BaseModel):
    type: ActivityLogType
    description: str
    severity: ActivityLogSeverity = ActivityLogSeverity.INFO
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ActivityLogResponse(BaseModel):
    id: str
    type: ActivityLogType
    description: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ActivityLogSearchRequest(BaseModel):
    query: Optional[str] = None
    types: Optional[List[ActivityLogType]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    user_id: Optional[str] = None
    page: int = 1
    page_size: int = 50


class ActivityLogSearchResponse(BaseModel):
    events: List[ActivityLogResponse]
    total_count: int
    page: int
    page_size: int


# Paginated responses
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


class PaginatedChatsResponse(BaseModel):
    items: List[ChatListResponse]
    total: int
    page: int
    size: int
    pages: int


class PaginatedQueriesResponse(BaseModel):
    items: List[QueryResponse]
    total: int
    page: int
    size: int
    pages: int
