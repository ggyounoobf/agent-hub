from sqlalchemy.ext.asyncio import AsyncSession
from app.services.activity_log_service import ActivityLogService
from app.models.schemas import ActivityLogCreate, ActivityLogType, ActivityLogSeverity
from typing import Optional, Dict, Any


class ActivityLogger:
    """Utility class for logging activities throughout the application."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = ActivityLogService()
    
    async def log_user_event(
        self,
        description: str,
        user_id: Optional[str] = None,
        severity: ActivityLogSeverity = ActivityLogSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a user-related event."""
        log_data = ActivityLogCreate(
            type=ActivityLogType.USER,
            description=description,
            severity=severity,
            user_id=user_id,
            metadata=metadata
        )
        return await self.service.create_activity_log(self.db, log_data)
    
    async def log_chat_event(
        self,
        description: str,
        user_id: Optional[str] = None,
        severity: ActivityLogSeverity = ActivityLogSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a chat-related event."""
        log_data = ActivityLogCreate(
            type=ActivityLogType.CHAT,
            description=description,
            severity=severity,
            user_id=user_id,
            metadata=metadata
        )
        return await self.service.create_activity_log(self.db, log_data)
    
    async def log_agent_event(
        self,
        description: str,
        user_id: Optional[str] = None,
        severity: ActivityLogSeverity = ActivityLogSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an agent-related event."""
        log_data = ActivityLogCreate(
            type=ActivityLogType.AGENT,
            description=description,
            severity=severity,
            user_id=user_id,
            metadata=metadata
        )
        return await self.service.create_activity_log(self.db, log_data)
    
    async def log_system_event(
        self,
        description: str,
        severity: ActivityLogSeverity = ActivityLogSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a system-related event."""
        log_data = ActivityLogCreate(
            type=ActivityLogType.SYSTEM,
            description=description,
            severity=severity,
            metadata=metadata
        )
        return await self.service.create_activity_log(self.db, log_data)
