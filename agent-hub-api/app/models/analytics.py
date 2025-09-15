from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date

class TimeSeriesData(BaseModel):
    """Time series data point."""
    date: date
    value: int

class AnalyticsOverview(BaseModel):
    """Overall platform analytics overview."""
    total_users: int
    total_chats: int
    total_queries: int
    total_files: int
    total_agents: int
    recent_users: int  # New users in the time period
    recent_chats: int  # New chats in the time period
    recent_queries: int  # New queries in the time period
    recent_files: int  # New files in the time period
    query_success_rate: float  # Percentage of successful queries
    most_active_users: List[Dict[str, Any]]  # Top 5 most active users

class AnalyticsOverviewResponse(BaseModel):
    """Response model for analytics overview."""
    data: AnalyticsOverview

class UsageStats(BaseModel):
    """Detailed usage statistics."""
    query_time_series: List[TimeSeriesData]
    chat_time_series: List[TimeSeriesData]
    file_time_series: List[TimeSeriesData]
    agent_usage: List[Dict[str, Any]]  # Usage count per agent
    file_types: List[Dict[str, Any]]  # Statistics per file type

class UsageStatsResponse(BaseModel):
    """Response model for usage statistics."""
    data: UsageStats

class AgentPerformance(BaseModel):
    """Agent performance metrics."""
    agent_performance: List[Dict[str, Any]]  # Performance data per agent
    tool_usage: Dict[str, List[Dict[str, Any]]]  # Tool usage per agent

class AgentPerformanceResponse(BaseModel):
    """Response model for agent performance."""
    data: AgentPerformance

class UserActivity(BaseModel):
    """User activity metrics."""
    user_registration_time_series: List[TimeSeriesData]
    active_users_time_series: List[TimeSeriesData]
    user_engagement: List[Dict[str, Any]]  # Queries per user

class UserActivityResponse(BaseModel):
    """Response model for user activity."""
    data: UserActivity