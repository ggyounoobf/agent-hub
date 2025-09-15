from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database.connection import get_db_session
from app.database.models import User, UserRole
from app.auth.dependencies import get_current_user
from app.services.analytics_service import AnalyticsService
from app.models.analytics import (
    AnalyticsOverviewResponse,
    UsageStatsResponse,
    AgentPerformanceResponse,
    UserActivityResponse,
    TimeSeriesData
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    days: int = Query(30, description="Number of days to look back for analytics"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get overall analytics overview for the platform."""
    # Only admins can access analytics
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can access analytics")
    
    analytics_service = AnalyticsService()
    overview = await analytics_service.get_overview_stats(db, days)
    return AnalyticsOverviewResponse(data=overview)

@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_statistics(
    days: int = Query(30, description="Number of days to look back for usage stats"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get detailed usage statistics."""
    # Only admins can access analytics
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can access analytics")
    
    analytics_service = AnalyticsService()
    usage_stats = await analytics_service.get_usage_stats(db, days)
    return UsageStatsResponse(data=usage_stats)

@router.get("/performance", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    days: int = Query(30, description="Number of days to look back for performance data"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get agent performance metrics."""
    # Only admins can access analytics
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can access analytics")
    
    analytics_service = AnalyticsService()
    performance = await analytics_service.get_agent_performance(db, days)
    return AgentPerformanceResponse(data=performance)

@router.get("/activity", response_model=UserActivityResponse)
async def get_user_activity(
    days: int = Query(30, description="Number of days to look back for user activity"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Get user activity metrics."""
    # Only admins can access analytics
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can access analytics")
    
    analytics_service = AnalyticsService()
    activity = await analytics_service.get_user_activity(db, days)
    return UserActivityResponse(data=activity)