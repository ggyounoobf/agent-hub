from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any, Tuple
import math

from app.database.models import User, Chat, Query, File
from app.models.schemas import (
    ChatCreate, ChatUpdate, ChatResponse, ChatListResponse,
    QueryRequest, QueryResponse, PaginatedChatsResponse, PaginatedQueriesResponse
)
from app.services.file_service import FileService
from app.models.file import FileCreate


class ChatService:
    async def create_chat(
        self,
        db: AsyncSession,
        user: User,
        chat_data: ChatCreate
    ) -> Chat:
        """Create a new chat with initial message."""
        # Create chat
        chat = Chat(
            user_id=user.id,
            title=chat_data.title or self._generate_title_from_message(chat_data.message)
        )
        
        db.add(chat)
        await db.flush()  # Get the chat ID
        
        # Create initial query
        query = Query(
            chat_id=chat.id,
            message=chat_data.message,
            selected_agents=chat_data.selected_agents,
            files_uploaded=self._process_files_metadata(chat_data.files),
            status="pending"
        )
        
        db.add(query)
        await db.commit()
        await db.refresh(chat)
        
        return chat

    async def create_chat_with_files(
        self,
        db: AsyncSession,
        user: User,
        chat_data: ChatCreate,
        file_records: List[File]
    ) -> Chat:
        """Create a new chat with initial message and associated files."""
        # Create chat
        chat = Chat(
            user_id=user.id,
            title=chat_data.title or self._generate_title_from_message(chat_data.message)
        )
        
        db.add(chat)
        await db.flush()  # Get the chat ID
        
        # Create initial query with detailed file metadata
        query = Query(
            chat_id=chat.id,
            message=chat_data.message,
            selected_agents=chat_data.selected_agents,
            files_uploaded=self._process_file_records_metadata(file_records),
            status="pending"
        )
        
        db.add(query)
        await db.flush()  # Get the query ID
        
        # Associate files with chat and query
        for file_record in file_records:
            file_record.chat_id = chat.id
            file_record.query_id = query.id
        
        await db.commit()
        await db.refresh(chat)
        
        return chat

    async def get_user_chats(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        size: int = 20
    ) -> PaginatedChatsResponse:
        """Get paginated list of user's chats."""
        offset = (page - 1) * size
        
        # Get total count
        total_result = await db.execute(
            select(func.count(Chat.id)).where(Chat.user_id == user_id)
        )
        # Fix: Handle None result and convert to Python int
        total_raw = total_result.scalar()
        total = int(total_raw) if total_raw is not None else 0
        
        # Get chats with query count
        chats_result = await db.execute(
            select(Chat, func.count(Query.id).label("query_count"))
            .outerjoin(Query)
            .where(Chat.user_id == user_id)
            .group_by(Chat.id)
            .order_by(desc(Chat.updated_at))
            .offset(offset)
            .limit(size)
        )
        
        chat_items = []
        for chat, query_count in chats_result:
            # Fix: Handle None query_count and convert to Python int
            count = int(query_count) if query_count is not None else 0
            chat_items.append(ChatListResponse(
                id=chat.id,
                title=chat.title,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                total_queries=count
            ))
        
        return PaginatedChatsResponse(
            items=chat_items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size)
        )

    async def get_chat(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str
    ) -> Optional[Chat]:
        """Get a specific chat with all queries."""
        result = await db.execute(
            select(Chat)
            .options(selectinload(Chat.queries))
            .where(Chat.id == chat_id)
            .where(Chat.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_chat_queries(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str,
        page: int = 1,
        size: int = 50
    ) -> PaginatedQueriesResponse:
        """Get paginated queries for a chat."""
        # Verify chat belongs to user
        chat = await db.execute(
            select(Chat).where(Chat.id == chat_id).where(Chat.user_id == user_id)
        )
        if not chat.scalar_one_or_none():
            raise ValueError("Chat not found or access denied")
        
        offset = (page - 1) * size
        
        # Get total count
        total_result = await db.execute(
            select(func.count(Query.id)).where(Query.chat_id == chat_id)
        )
        # Fix: Handle None result and convert to Python int
        total_raw = total_result.scalar()
        total = int(total_raw) if total_raw is not None else 0
        
        # Get queries
        queries_result = await db.execute(
            select(Query)
            .where(Query.chat_id == chat_id)
            .order_by(Query.created_at)
            .offset(offset)
            .limit(size)
        )
        
        queries = queries_result.scalars().all()
        query_items = [QueryResponse.from_orm(query) for query in queries]
        
        return PaginatedQueriesResponse(
            items=query_items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size)
        )

    async def update_chat(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str,
        update_data: ChatUpdate
    ) -> Optional[Chat]:
        """Update chat information."""
        result = await db.execute(
            update(Chat)
            .where(Chat.id == chat_id)
            .where(Chat.user_id == user_id)
            .values(**update_data.dict(exclude_unset=True))
        )
        
        if result.rowcount == 0:
            return None
        
        await db.commit()
        return await self.get_chat(db, chat_id, user_id)

    async def delete_chat(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str
    ) -> bool:
        """Delete a chat and all its queries."""
        result = await db.execute(
            delete(Chat)
            .where(Chat.id == chat_id)
            .where(Chat.user_id == user_id)
        )
        await db.commit()
        return result.rowcount > 0

    async def add_query_to_chat(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str,
        query_data: QueryRequest
    ) -> Optional[Query]:
        """Add a new query to an existing chat."""
        # Verify chat belongs to user
        chat = await db.execute(
            select(Chat).where(Chat.id == chat_id).where(Chat.user_id == user_id)
        )
        if not chat.scalar_one_or_none():
            return None
        
        # Create query
        query = Query(
            chat_id=chat_id,
            message=query_data.message,
            selected_agents=query_data.selected_agents,
            files_uploaded=self._process_files_metadata(query_data.files),
            status="pending"
        )
        
        db.add(query)
        
        # Update chat timestamp
        await db.execute(
            update(Chat)
            .where(Chat.id == chat_id)
            .values(updated_at=datetime.utcnow())
        )
        
        await db.commit()
        await db.refresh(query)
        
        return query

    async def add_query_to_chat_with_files(
        self,
        db: AsyncSession,
        chat_id: str,
        user_id: str,
        query_data: QueryRequest,
        file_records: List[File]
    ) -> Optional[Query]:
        """Add a new query to an existing chat with associated files."""
        # Verify chat belongs to user
        chat = await db.execute(
            select(Chat).where(Chat.id == chat_id).where(Chat.user_id == user_id)
        )
        if not chat.scalar_one_or_none():
            return None
        
        # Create query with detailed file metadata
        query = Query(
            chat_id=chat_id,
            message=query_data.message,
            selected_agents=query_data.selected_agents,
            files_uploaded=self._process_file_records_metadata(file_records),
            status="pending"
        )
        
        db.add(query)
        await db.flush()  # Get the query ID
        
        # Associate files with query
        for file_record in file_records:
            file_record.chat_id = chat_id
            file_record.query_id = query.id
        
        # Update chat timestamp
        await db.execute(
            update(Chat)
            .where(Chat.id == chat_id)
            .values(updated_at=datetime.utcnow())
        )
        
        await db.commit()
        await db.refresh(query)
        
        return query

    async def update_query_response(
        self,
        db: AsyncSession,
        query_id: str,
        response: str,
        agent_used: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None,
        status: str = "completed"
    ) -> Optional[Query]:
        """Update query with response from agent."""
        result = await db.execute(
            update(Query)
            .where(Query.id == query_id)
            .values(
                response=response,
                agent_used=agent_used,
                token_usage=token_usage,
                status=status,
                updated_at=datetime.utcnow()
            )
        )
        
        if result.rowcount == 0:
            return None
        
        await db.commit()
        
        # Get updated query
        query_result = await db.execute(select(Query).where(Query.id == query_id))
        return query_result.scalar_one_or_none()

    async def update_query_error(
        self,
        db: AsyncSession,
        query_id: str,
        error_message: str
    ) -> Optional[Query]:
        """Update query with error information."""
        result = await db.execute(
            update(Query)
            .where(Query.id == query_id)
            .values(
                status="failed",
                error_message=error_message,
                updated_at=datetime.utcnow()
            )
        )
        
        if result.rowcount == 0:
            return None
        
        await db.commit()
        
        # Get updated query
        query_result = await db.execute(select(Query).where(Query.id == query_id))
        return query_result.scalar_one_or_none()

    def _generate_title_from_message(self, message: str) -> str:
        """Generate a chat title from the first message."""
        # Take first 50 characters and add ellipsis if longer
        title = message.strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title

    def _process_files_metadata(self, files: Optional[List[str]]) -> Optional[List[Dict[str, Any]]]:
        """Process file names into metadata format."""
        if not files:
            return None
        
        return [
            {
                "name": filename,
                "uploaded_at": datetime.utcnow().isoformat()
            } 
            for filename in files
        ]
    
    def _process_file_records_metadata(self, file_records: List[File]) -> List[Dict[str, Any]]:
        """Process actual file records into detailed metadata format."""
        return [
            {
                "id": file_record.id,
                "name": file_record.name,
                "uploaded_at": file_record.uploaded_at.isoformat() if file_record.uploaded_at else datetime.utcnow().isoformat()
            }
            for file_record in file_records
        ]
