from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from app.database.models import ActivityLog, ActivityLogType, ActivityLogSeverity, User
from app.models.schemas import ActivityLogCreate, ActivityLogResponse


class ActivityLogService:
    """Service for managing activity logs."""

    async def create_activity_log(
        self,
        db: AsyncSession,
        log_data: ActivityLogCreate
    ) -> ActivityLog:
        """Create a new activity log entry."""
        # Convert string values to enum values if needed
        log_type = log_data.type
        if isinstance(log_type, str):
            log_type = ActivityLogType(log_type.upper())
            
        log_severity = log_data.severity
        if isinstance(log_severity, str):
            log_severity = ActivityLogSeverity(log_severity.upper())
        
        db_log = ActivityLog(
            type=log_type,
            severity=log_severity,
            description=log_data.description,
            user_id=log_data.user_id,
            metadata_json=log_data.metadata
        )
        
        db.add(db_log)
        await db.commit()
        await db.refresh(db_log)
        return db_log

    async def get_recent_activity(
        self,
        db: AsyncSession,
        limit: int = 50,
        types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ActivityLog]:
        """Get recent activity logs with optional filtering."""
        query = select(ActivityLog).order_by(desc(ActivityLog.timestamp))
        
        # Apply filters
        if types:
            type_enums = []
            for t in types:
                if isinstance(t, str):
                    type_enums.append(ActivityLogType(t.upper()))
                else:
                    type_enums.append(t)
            query = query.where(ActivityLog.type.in_(type_enums))
            
        if user_id:
            query = query.where(ActivityLog.user_id == user_id)
            
        if start_time:
            query = query.where(ActivityLog.timestamp >= start_time)
            
        if end_time:
            query = query.where(ActivityLog.timestamp <= end_time)
            
        query = query.limit(min(limit, 100))  # Cap at 100
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_activity_by_time_range(
        self,
        db: AsyncSession,
        start_time: datetime,
        end_time: datetime,
        types: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> List[ActivityLog]:
        """Get activity logs within a specific time range."""
        query = select(ActivityLog).where(
            ActivityLog.timestamp >= start_time,
            ActivityLog.timestamp <= end_time
        ).order_by(desc(ActivityLog.timestamp))
        
        # Apply filters
        if types:
            type_enums = []
            for t in types:
                if isinstance(t, str):
                    type_enums.append(ActivityLogType(t.upper()))
                else:
                    type_enums.append(t)
            query = query.where(ActivityLog.type.in_(type_enums))
            
        if user_id:
            query = query.where(ActivityLog.user_id == user_id)
            
        result = await db.execute(query)
        return result.scalars().all()

    async def search_activity(
        self,
        db: AsyncSession,
        query_text: str,
        types: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[ActivityLog], int]:
        """Search activity logs by text query and filters."""
        # Base query
        query = select(ActivityLog)
        
        # Apply text search (simple implementation - could be enhanced with full-text search)
        if query_text:
            query = query.where(
                ActivityLog.description.contains(query_text)
            )
        
        # Apply filters
        if types:
            type_enums = []
            for t in types:
                if isinstance(t, str):
                    type_enums.append(ActivityLogType(t.upper()))
                else:
                    type_enums.append(t)
            query = query.where(ActivityLog.type.in_(type_enums))
            
        if user_id:
            query = query.where(ActivityLog.user_id == user_id)
            
        if start_time:
            query = query.where(ActivityLog.timestamp >= start_time)
            
        if end_time:
            query = query.where(ActivityLog.timestamp <= end_time)
            
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(desc(ActivityLog.timestamp)).offset(offset).limit(page_size)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return logs, total_count

    def serialize_log(self, log: ActivityLog) -> dict:
        """Convert an ActivityLog object to a dictionary for API responses."""
        return {
            "id": log.id,
            "type": log.type.value,
            "description": log.description,
            "timestamp": log.timestamp.isoformat(),
            "metadata": log.metadata_json or {}
        }
