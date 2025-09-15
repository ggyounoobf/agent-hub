from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, Form
from fastapi import File as FastAPIFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.database.connection import get_db_session
from app.services.chat_service import ChatService
from app.auth.dependencies import get_current_user
from app.models.schemas import (
    ChatCreate, ChatUpdate, ChatResponse, ChatListResponse,
    QueryRequest, QueryResponse, PaginatedChatsResponse, PaginatedQueriesResponse
)
from app.database.models import User
from app.services.file_service import FileService
from app.models.file import FileCreate
from app.utils.activity_logger import ActivityLogger

router = APIRouter(prefix="/chats", tags=["Chats"])
chat_service = ChatService()
file_service = FileService()


@router.post("/", response_model=ChatResponse)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat with initial message."""
    try:
        chat = await chat_service.create_chat(db, current_user, chat_data)
        
        # Log chat creation event
        activity_logger = ActivityLogger(db)
        await activity_logger.log_chat_event(
            f"New chat session started by user ID {current_user.id}",
            user_id=str(current_user.id),
            metadata={"chat_id": str(chat.id)}
        )
        
        # Fix: Convert SQLAlchemy columns to strings to avoid type issues
        chat_id = str(getattr(chat, 'id', ''))
        current_user_id = str(getattr(current_user, 'id', ''))
        
        # Convert to response model with queries
        chat_with_queries = await chat_service.get_chat(db, chat_id, current_user_id)
        return ChatResponse.from_orm(chat_with_queries)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create chat: {str(e)}"
        )


@router.get("/", response_model=PaginatedChatsResponse)
async def get_user_chats(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get paginated list of user's chats."""
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20
    
    current_user_id = str(getattr(current_user, 'id', ''))
    return await chat_service.get_user_chats(db, current_user_id, page, size)


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific chat with all queries."""
    current_user_id = str(getattr(current_user, 'id', ''))
    chat = await chat_service.get_chat(db, chat_id, current_user_id)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    return ChatResponse.from_orm(chat)


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    update_data: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update chat information."""
    current_user_id = str(getattr(current_user, 'id', ''))
    chat = await chat_service.update_chat(db, chat_id, current_user_id, update_data)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    return ChatResponse.from_orm(chat)


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chat and all its queries."""
    current_user_id = str(getattr(current_user, 'id', ''))
    success = await chat_service.delete_chat(db, chat_id, current_user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    # Log chat deletion event
    activity_logger = ActivityLogger(db)
    await activity_logger.log_chat_event(
        f"Chat history deleted by user ID {current_user.id}: chat ID {chat_id}",
        user_id=str(current_user.id),
        metadata={"chat_id": chat_id}
    )
    
    return {"message": "Chat deleted successfully"}


@router.get("/{chat_id}/queries", response_model=PaginatedQueriesResponse)
async def get_chat_queries(
    chat_id: str,
    page: int = 1,
    size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get paginated queries for a chat."""
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 50
    
    try:
        current_user_id = str(getattr(current_user, 'id', ''))
        return await chat_service.get_chat_queries(db, chat_id, current_user_id, page, size)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{chat_id}/queries", response_model=QueryResponse)
async def add_query_to_chat(
    chat_id: str,
    query_data: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Add a new query to an existing chat."""
    current_user_id = str(getattr(current_user, 'id', ''))
    query = await chat_service.add_query_to_chat(db, chat_id, current_user_id, query_data)
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    # Log query addition event
    activity_logger = ActivityLogger(db)
    await activity_logger.log_chat_event(
        f"User sent message in chat ID {chat_id}",
        user_id=str(current_user.id),
        metadata={"chat_id": chat_id, "query_id": str(query.id)}
    )
    
    return QueryResponse.from_orm(query)


# File upload endpoint for chat creation
@router.post("/create-with-files", response_model=ChatResponse)
async def create_chat_with_files(
    message: str = Form(...),
    title: Optional[str] = Form(None),
    selected_agents: Optional[str] = Form(None),  # Comma-separated string
    files: List[UploadFile] = FastAPIFile(default=[]),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat with file uploads."""
    # Process selected agents
    agent_list = []
    if selected_agents:
        agent_list = [agent.strip() for agent in selected_agents.split(",") if agent.strip()]
    
    # Process uploaded files
    file_records = []
    if files:
        for uploaded_file in files:
            if uploaded_file.filename:
                file_create = FileCreate(
                    name=uploaded_file.filename,
                    content_type=uploaded_file.content_type or "application/octet-stream",
                    size=0,  # Will be updated after reading
                )
                
                # Read file content
                content = await uploaded_file.read()
                file_create.size = len(content)
                
                # Save file
                file_record = await file_service.create_file(
                    db, file_create, current_user.id, content
                )
                file_records.append(file_record)
    
    # Create chat with files
    chat_data = ChatCreate(
        title=title,
        message=message,
        files=[f.name for f in file_records],
        selected_agents=agent_list
    )
    
    try:
        chat = await chat_service.create_chat_with_files(db, current_user, chat_data, file_records)
        
        # Log chat creation with files event
        activity_logger = ActivityLogger(db)
        await activity_logger.log_chat_event(
            f"New chat session started with files by user ID {current_user.id}",
            user_id=str(current_user.id),
            metadata={
                "chat_id": str(chat.id),
                "file_count": len(file_records),
                "agents_used": agent_list
            }
        )
        
        chat_id = str(getattr(chat, 'id', ''))
        current_user_id = str(getattr(current_user, 'id', ''))
        
        chat_with_queries = await chat_service.get_chat(db, chat_id, current_user_id)
        return ChatResponse.from_orm(chat_with_queries)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create chat: {str(e)}"
        )


# File upload endpoint for adding query to existing chat
@router.post("/{chat_id}/queries-with-files", response_model=QueryResponse)
async def add_query_with_files(
    chat_id: str,
    message: str = Form(...),
    selected_agents: Optional[str] = Form(None),
    files: List[UploadFile] = FastAPIFile(default=[]),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Add a new query with file uploads to an existing chat."""
    # Process selected agents
    agent_list = []
    if selected_agents:
        agent_list = [agent.strip() for agent in selected_agents.split(",") if agent.strip()]
    
    # Process uploaded files
    file_records = []
    if files:
        for uploaded_file in files:
            if uploaded_file.filename:
                file_create = FileCreate(
                    name=uploaded_file.filename,
                    content_type=uploaded_file.content_type or "application/octet-stream",
                    size=0,  # Will be updated after reading
                )
                
                # Read file content
                content = await uploaded_file.read()
                file_create.size = len(content)
                
                # Save file
                file_record = await file_service.create_file(
                    db, file_create, current_user.id, content
                )
                file_records.append(file_record)
    
    # Get file names for query
    file_names = [f.name for f in file_records]
    
    query_data = QueryRequest(
        message=message,
        files=file_names,
        selected_agents=agent_list
    )
    
    current_user_id = str(getattr(current_user, 'id', ''))
    
    query = await chat_service.add_query_to_chat_with_files(db, chat_id, current_user_id, query_data, file_records)
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    # Log query with files addition event
    activity_logger = ActivityLogger(db)
    await activity_logger.log_chat_event(
        f"User sent message with files in chat ID {chat_id}",
        user_id=str(current_user.id),
        metadata={
            "chat_id": chat_id,
            "query_id": str(query.id),
            "file_count": len(file_records),
            "agents_used": agent_list
        }
    )
    
    return QueryResponse.from_orm(query)