from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, and_, Integer, case
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from app.database.models import User, Chat, Query, File, Agent, AgentTool
from app.models.analytics import (
    AnalyticsOverview,
    UsageStats,
    AgentPerformance,
    UserActivity,
    TimeSeriesData
)

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for retrieving analytics data from the database."""
    
    async def get_overview_stats(self, db: AsyncSession, days: int = 30) -> AnalyticsOverview:
        """Get overall platform statistics."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get total counts
        total_users = await db.scalar(select(func.count(User.id)))
        total_chats = await db.scalar(select(func.count(Chat.id)))
        total_queries = await db.scalar(select(func.count(Query.id)))
        total_files = await db.scalar(select(func.count(File.id)))
        total_agents = await db.scalar(select(func.count(Agent.id)))
        
        # Get recent counts (last N days)
        recent_users = await db.scalar(
            select(func.count(User.id)).where(User.created_at >= start_date)
        )
        recent_chats = await db.scalar(
            select(func.count(Chat.id)).where(Chat.created_at >= start_date)
        )
        recent_queries = await db.scalar(
            select(func.count(Query.id)).where(Query.created_at >= start_date)
        )
        recent_files = await db.scalar(
            select(func.count(File.id)).where(File.uploaded_at >= start_date)
        )
        
        # Get query success rate
        total_query_results = await db.execute(
            select(
                func.count(Query.id).label("total"),
                func.sum(case((Query.status == "completed", 1), else_=0)).label("completed")
            )
        )
        query_stats = total_query_results.first()
        success_rate = (
            (query_stats.completed / query_stats.total * 100) 
            if query_stats.total > 0 else 0
        )
        
        # Get most active users (top 5)
        active_users_result = await db.execute(
            select(
                User.username,
                func.count(Query.id).label("query_count")
            )
            .join(Chat, Chat.user_id == User.id)
            .join(Query, Query.chat_id == Chat.id)
            .where(Query.created_at >= start_date)
            .group_by(User.id, User.username)
            .order_by(func.count(Query.id).desc())
            .limit(5)
        )
        most_active_users = [
            {"username": row.username, "query_count": row.query_count}
            for row in active_users_result.fetchall()
        ]
        
        return AnalyticsOverview(
            total_users=total_users or 0,
            total_chats=total_chats or 0,
            total_queries=total_queries or 0,
            total_files=total_files or 0,
            total_agents=total_agents or 0,
            recent_users=recent_users or 0,
            recent_chats=recent_chats or 0,
            recent_queries=recent_queries or 0,
            recent_files=recent_files or 0,
            query_success_rate=round(success_rate, 2),
            most_active_users=most_active_users
        )
    
    async def get_usage_stats(self, db: AsyncSession, days: int = 30) -> UsageStats:
        """Get detailed usage statistics."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Generate time series data for queries
        query_time_series = await self._get_time_series_data(
            db, Query.created_at, start_date, end_date, "queries"
        )
        
        # Generate time series data for chats
        chat_time_series = await self._get_time_series_data(
            db, Chat.created_at, start_date, end_date, "chats"
        )
        
        # Generate time series data for files
        file_time_series = await self._get_time_series_data(
            db, File.uploaded_at, start_date, end_date, "files"
        )
        
        # Get agent usage statistics
        agent_usage_result = await db.execute(
            select(
                Query.agent_used,
                func.count(Query.id).label("usage_count")
            )
            .where(
                Query.created_at >= start_date,
                Query.agent_used.isnot(None)
            )
            .group_by(Query.agent_used)
            .order_by(func.count(Query.id).desc())
        )
        agent_usage = [
            {"agent_name": row.agent_used, "usage_count": row.usage_count}
            for row in agent_usage_result.fetchall()
        ]
        
        # Get file type statistics
        file_type_result = await db.execute(
            select(
                File.content_type,
                func.count(File.id).label("count"),
                func.sum(File.size).label("total_size")
            )
            .where(File.uploaded_at >= start_date)
            .group_by(File.content_type)
            .order_by(func.count(File.id).desc())
        )
        file_types = [
            {
                "content_type": row.content_type,
                "count": row.count,
                "total_size": row.total_size or 0
            }
            for row in file_type_result.fetchall()
        ]
        
        return UsageStats(
            query_time_series=query_time_series,
            chat_time_series=chat_time_series,
            file_time_series=file_time_series,
            agent_usage=agent_usage,
            file_types=file_types
        )
    
    async def get_agent_performance(self, db: AsyncSession, days: int = 30) -> AgentPerformance:
        """Get agent performance metrics."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get agent success rates
        agent_stats_result = await db.execute(
            select(
                Query.agent_used,
                func.count(Query.id).label("total"),
                func.sum(case((Query.status == "completed", 1), else_=0)).label("completed"),

                func.avg(func.cast(Query.token_usage.op('->>')('total_tokens'), Integer)).label("avg_tokens")
            )
            .where(
                Query.created_at >= start_date,
                Query.agent_used.isnot(None)
            )
            .group_by(Query.agent_used)
        )
        
        agent_performance = []
        for row in agent_stats_result.fetchall():
            success_rate = (
                (row.completed / row.total * 100) 
                if row.total > 0 else 0
            )
            agent_performance.append({
                "agent_name": row.agent_used,
                "total_queries": row.total,
                "success_rate": round(success_rate, 2),
                "average_tokens": int(float(row.avg_tokens)) if row.avg_tokens else 0
            })
        
        # Get tool usage per agent
        tool_usage_result = await db.execute(
            select(
                Agent.name.label("agent_name"),
                AgentTool.name.label("tool_name"),
                func.count().label("usage_count")
            )
            .select_from(Agent)
            .join(AgentTool, AgentTool.agent_id == Agent.id)
            .group_by(Agent.name, AgentTool.name)
            .order_by(Agent.name, func.count().desc())
        )
        
        tool_usage = {}
        for row in tool_usage_result.fetchall():
            if row.agent_name not in tool_usage:
                tool_usage[row.agent_name] = []
            tool_usage[row.agent_name].append({
                "tool_name": row.tool_name,
                "usage_count": row.usage_count
            })
        
        return AgentPerformance(
            agent_performance=agent_performance,
            tool_usage=tool_usage
        )
    
    async def get_user_activity(self, db: AsyncSession, days: int = 30) -> UserActivity:
        """Get user activity metrics."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get user registration time series
        user_time_series = await self._get_time_series_data(
            db, User.created_at, start_date, end_date, "registrations"
        )
        
        # Get active users per day
        active_users_result = await db.execute(
            select(
                func.date(Query.created_at).label("date"),
                func.count(func.distinct(Chat.user_id)).label("active_users")
            )
            .join(Chat, Chat.id == Query.chat_id)
            .where(Query.created_at >= start_date)
            .group_by(func.date(Query.created_at))
            .order_by(func.date(Query.created_at))
        )
        
        active_users_data = [
            TimeSeriesData(
                date=row.date,
                value=row.active_users
            )
            for row in active_users_result.fetchall()
        ]
        
        # Get user engagement (queries per user)
        user_engagement_result = await db.execute(
            select(
                User.username,
                func.count(Query.id).label("query_count")
            )
            .join(Chat, Chat.user_id == User.id)
            .join(Query, Query.chat_id == Chat.id)
            .where(Query.created_at >= start_date)
            .group_by(User.id, User.username)
            .order_by(func.count(Query.id).desc())
        )
        
        user_engagement = [
            {"username": row.username, "query_count": row.query_count}
            for row in user_engagement_result.fetchall()
        ]
        
        return UserActivity(
            user_registration_time_series=user_time_series,
            active_users_time_series=active_users_data,
            user_engagement=user_engagement
        )
    
    async def _get_time_series_data(
        self, 
        db: AsyncSession, 
        date_column, 
        start_date: datetime, 
        end_date: datetime, 
        metric_name: str
    ) -> List[TimeSeriesData]:
        """Generate time series data for a given metric."""
        # Generate date series
        date_series = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_series.append(current_date)
            current_date += timedelta(days=1)
        
        # Get actual data
        if metric_name == "queries":
            result = await db.execute(
                select(
                    func.date(date_column).label("date"),
                    func.count().label("count")
                )
                .where(date_column >= start_date)
                .group_by(func.date(date_column))
                .order_by(func.date(date_column))
            )
        elif metric_name == "chats":
            result = await db.execute(
                select(
                    func.date(date_column).label("date"),
                    func.count().label("count")
                )
                .where(date_column >= start_date)
                .group_by(func.date(date_column))
                .order_by(func.date(date_column))
            )
        elif metric_name == "files":
            result = await db.execute(
                select(
                    func.date(date_column).label("date"),
                    func.count().label("count")
                )
                .where(date_column >= start_date)
                .group_by(func.date(date_column))
                .order_by(func.date(date_column))
            )
        elif metric_name == "registrations":
            result = await db.execute(
                select(
                    func.date(date_column).label("date"),
                    func.count().label("count")
                )
                .where(date_column >= start_date)
                .group_by(func.date(date_column))
                .order_by(func.date(date_column))
            )
        else:
            return []
        
        # Create a dictionary for quick lookup
        data_dict = {
            row.date: row.count 
            for row in result.fetchall()
        }
        
        # Fill in missing dates with 0
        time_series = [
            TimeSeriesData(
                date=date,
                value=data_dict.get(date, 0)
            )
            for date in date_series
        ]
        
        return time_series