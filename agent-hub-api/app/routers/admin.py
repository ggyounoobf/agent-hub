from fastapi import APIRouter, Depends, HTTPException, status, Query as FastAPIQuery
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta

from app.database.connection import get_db_session
from app.auth.dependencies import get_current_admin_user
from app.database.models import User, Chat, Query, ActivityLog, ActivityLogType
from app.models.schemas import (
    ChatResponse,
    ActivityLogCreate, 
    ActivityLogResponse, 
    ActivityLogSearchRequest,
    ActivityLogSearchResponse
)
from app.services.activity_log_service import ActivityLogService
from sqlalchemy import select, func, text

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/chats", response_model=List[dict])
async def get_all_chats(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all user chats (admin only)."""
    try:
        # Query to get chats with user information and query count
        query = select(
            Chat.id,
            Chat.title,
            Chat.created_at,
            Chat.updated_at,
            Chat.user_id,
            User.email.label('user_email'),
            User.full_name.label('user_name'),
            func.count(Query.id).label('query_count')
        ).join(User, Chat.user_id == User.id).outerjoin(
            Query, Chat.id == Query.chat_id
        ).group_by(Chat.id, User.id).order_by(Chat.updated_at.desc())
        
        result = await db.execute(query)
        chats = result.fetchall()
        
        return [
            {
                "id": chat.id,
                "title": chat.title,
                "userId": chat.user_id,
                "userEmail": chat.user_email,
                "userName": chat.user_name,
                "messageCount": chat.query_count or 0,
                "createdAt": chat.created_at,
                "updatedAt": chat.updated_at
            }
            for chat in chats
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chats: {str(e)}"
        )


@router.get("/chats/{chat_id}/queries")
async def get_chat_queries(
    chat_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get queries for a specific chat (admin only)."""
    try:
        query = select(Query).where(Query.chat_id == chat_id).order_by(Query.created_at)
        result = await db.execute(query)
        queries = result.scalars().all()
        
        return [
            {
                "id": q.id,
                "chat_id": q.chat_id,
                "message": q.message,
                "response": q.response,
                "agent_used": q.agent_used,
                "status": q.status,
                "created_at": q.created_at
            }
            for q in queries
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat queries: {str(e)}"
        )


@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chat and all its messages (admin only)."""
    try:
        # First, delete all queries in the chat
        queries_result = await db.execute(select(Query).where(Query.chat_id == chat_id))
        queries = queries_result.scalars().all()
        
        for query in queries:
            await db.delete(query)
        
        # Then delete the chat
        chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
        chat = chat_result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        await db.delete(chat)
        await db.commit()
        
        return {"message": "Chat deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat: {str(e)}"
        )


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get detailed system statistics (admin only)."""
    try:
        # Count total users
        users_result = await db.execute(select(func.count(User.id)))
        total_users = users_result.scalar() or 0
        
        # Count total chats
        chats_result = await db.execute(select(func.count(Chat.id)))
        total_chats = chats_result.scalar() or 0
        
        # Count total queries
        queries_result = await db.execute(select(func.count(Query.id)))
        total_queries = queries_result.scalar() or 0
        
        # Count active users (users with chats in the last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users_result = await db.execute(
            select(func.count(func.distinct(Chat.user_id)))
            .where(Chat.updated_at >= thirty_days_ago)
        )
        active_users = active_users_result.scalar() or 0
        
        # Count queries in the last 24 hours
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        recent_queries_result = await db.execute(
            select(func.count(Query.id))
            .where(Query.created_at >= twenty_four_hours_ago)
        )
        recent_queries = recent_queries_result.scalar() or 0
        
        # Count chats in the last 24 hours
        recent_chats_result = await db.execute(
            select(func.count(Chat.id))
            .where(Chat.created_at >= twenty_four_hours_ago)
        )
        recent_chats = recent_chats_result.scalar() or 0
        
        # Get activity log counts by type
        activity_counts_result = await db.execute(
            select(ActivityLog.type, func.count(ActivityLog.id))
            .group_by(ActivityLog.type)
        )
        activity_counts = activity_counts_result.fetchall()
        activity_stats = {str(count[0]).lower(): count[1] for count in activity_counts}
        
        # Get top 5 most active users
        top_users_result = await db.execute(
            select(
                User.id,
                User.email,
                User.full_name,
                func.count(Query.id).label('query_count')
            )
            .join(Chat, User.id == Chat.user_id)
            .join(Query, Chat.id == Query.chat_id)
            .group_by(User.id)
            .order_by(text('query_count DESC'))
            .limit(5)
        )
        top_users = top_users_result.fetchall()
        top_users_list = [
            {
                "id": user.id,
                "email": user.email,
                "fullName": user.full_name,
                "queryCount": user.query_count
            }
            for user in top_users
        ]
        
        return {
            "users": {
                "total": total_users,
                "active": active_users
            },
            "chats": {
                "total": total_chats,
                "recent24h": recent_chats
            },
            "queries": {
                "total": total_queries,
                "recent24h": recent_queries
            },
            "activity": activity_stats,
            "topUsers": top_users_list,
            "systemHealth": "healthy"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stats: {str(e)}"
        )


# Activity Logging Endpoints
@router.get("/activity/recent", response_model=List[ActivityLogResponse])
async def get_recent_activity(
    limit: int = FastAPIQuery(default=50, le=100),
    types: Optional[str] = FastAPIQuery(default=None),
    user_id: Optional[str] = FastAPIQuery(default=None),
    start_time: Optional[datetime] = FastAPIQuery(default=None),
    end_time: Optional[datetime] = FastAPIQuery(default=None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get recent activity logs with optional filtering."""
    try:
        # Parse types parameter
        type_list = types.split(",") if types else None
        
        service = ActivityLogService()
        logs = await service.get_recent_activity(
            db, limit, type_list, user_id, start_time, end_time
        )
        
        return [ActivityLogResponse(
            id=log.id,
            type=log.type,
            description=log.description,
            timestamp=log.timestamp,
            metadata=log.metadata_json
        ) for log in logs]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity logs: {str(e)}"
        )


@router.get("/activity/range", response_model=List[ActivityLogResponse])
async def get_activity_by_time_range(
    start_time: datetime,
    end_time: datetime,
    types: Optional[str] = FastAPIQuery(default=None),
    user_id: Optional[str] = FastAPIQuery(default=None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get activity logs within a specific time range."""
    try:
        # Parse types parameter
        type_list = types.split(",") if types else None
        
        service = ActivityLogService()
        logs = await service.get_activity_by_time_range(
            db, start_time, end_time, type_list, user_id
        )
        
        return [ActivityLogResponse(
            id=log.id,
            type=log.type,
            description=log.description,
            timestamp=log.timestamp,
            metadata=log.metadata_json
        ) for log in logs]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity logs: {str(e)}"
        )


@router.post("/activity/search", response_model=ActivityLogSearchResponse)
async def search_activity(
    search_request: ActivityLogSearchRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Search activity logs by text query and filters."""
    try:
        service = ActivityLogService()
        logs, total_count = await service.search_activity(
            db,
            search_request.query or "",
            [t.value for t in search_request.types] if search_request.types else None,
            search_request.start_time,
            search_request.end_time,
            search_request.user_id,
            search_request.page,
            search_request.page_size
        )
        
        events = [ActivityLogResponse(
            id=log.id,
            type=log.type,
            description=log.description,
            timestamp=log.timestamp,
            metadata=log.metadata_json
        ) for log in logs]
        
        return ActivityLogSearchResponse(
            events=events,
            total_count=total_count,
            page=search_request.page,
            page_size=search_request.page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search activity logs: {str(e)}"
        )
