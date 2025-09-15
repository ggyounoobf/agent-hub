from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Boolean, JSON, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import uuid
import enum


def generate_uuid():
    return str(uuid.uuid4())


class UserRole(enum.Enum):
    """User role enumeration for role-based access control."""
    ADMIN = "admin"
    USER = "user"


class ActivityLogType(enum.Enum):
    """Activity log type enumeration for categorizing events."""
    USER = "USER"
    CHAT = "CHAT"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


class ActivityLogSeverity(enum.Enum):
    """Activity log severity levels."""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    type = Column(Enum(ActivityLogType), nullable=False, index=True)
    severity = Column(Enum(ActivityLogSeverity), default=ActivityLogSeverity.INFO, nullable=False)
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)  # Store additional event-specific data

    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    github_id = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)  # For credential-based authentication
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)  # User role for RBAC
    avatar_url = Column(String, nullable=True)
    github_token = Column(Text, nullable=True)  # Encrypted GitHub access token
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    owned_agents = relationship("AgentOwnership", back_populates="user", cascade="all, delete-orphan", foreign_keys="AgentOwnership.user_id")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    agent_requests = relationship("AgentRequest", back_populates="user", cascade="all, delete-orphan", foreign_keys="AgentRequest.user_id")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="chats")
    queries = relationship("Query", back_populates="chat", cascade="all, delete-orphan")
    files = relationship("File", back_populates="chat", cascade="all, delete-orphan")


class Query(Base):
    __tablename__ = "queries"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    agent_used = Column(String, nullable=True)
    token_usage = Column(JSON, nullable=True)
    files_uploaded = Column(JSON, nullable=True)  # Store file metadata
    selected_agents = Column(JSON, nullable=True)  # Store selected agent names
    status = Column(String, default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    chat = relationship("Chat", back_populates="queries")
    files = relationship("File", back_populates="query", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)  # Path to the stored file
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=True)
    query_id = Column(String, ForeignKey("queries.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="files")
    query = relationship("Query", back_populates="files")
    user = relationship("User")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owners = relationship("AgentOwnership", back_populates="agent", cascade="all, delete-orphan")
    tools = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")
    requests = relationship("AgentRequest", back_populates="agent", cascade="all, delete-orphan")


class AgentTool(Base):
    __tablename__ = "agent_tools"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    agent = relationship("Agent", back_populates="tools")


class AgentRequest(Base):
    __tablename__ = "agent_requests"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    justification = Column(Text, nullable=True)  # User provided reason for requesting access
    status = Column(String, default="pending")  # pending, processing, completed, failed
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)  # Admin who reviewed the request
    review_reason = Column(Text, nullable=True)  # Reason for approval/rejection
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="agent_requests", foreign_keys=[user_id])
    agent = relationship("Agent", back_populates="requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class AgentOwnership(Base):
    __tablename__ = "agent_ownership"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    granted_by = Column(String, ForeignKey("users.id"), nullable=True)  # Admin who granted the ownership

    # Relationships
    user = relationship("User", back_populates="owned_agents", foreign_keys=[user_id])
    agent = relationship("Agent", back_populates="owners")
    grantor = relationship("User", foreign_keys=[granted_by])


class UserPDFContext(Base):
    __tablename__ = "user_pdf_contexts"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    file_id = Column(String, ForeignKey("files.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Extracted text content
    summary = Column(Text, nullable=True)   # Generated summary
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    file = relationship("File")
