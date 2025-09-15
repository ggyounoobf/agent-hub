import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.database.models import ActivityLog, ActivityLogType, ActivityLogSeverity, User
from app.services.activity_log_service import ActivityLogService
from app.models.schemas import ActivityLogCreate

# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create a test database and session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    # Close all connections
    await engine.dispose()

@pytest.mark.asyncio
async def test_activity_log_creation(test_db):
    """Test creating an activity log entry."""
    # Create a test user first
    test_user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)
    
    # Create activity log service
    service = ActivityLogService()
    
    # Create activity log entry
    log_data = ActivityLogCreate(
        type=ActivityLogType.USER,
        description="Test user activity",
        severity=ActivityLogSeverity.INFO,
        user_id=test_user.id,
        metadata={"test": "data"}
    )
    
    # Test creating activity log
    log = await service.create_activity_log(test_db, log_data)
    
    # Verify the log was created correctly
    assert log is not None
    assert log.type == ActivityLogType.USER
    assert log.description == "Test user activity"
    assert log.severity == ActivityLogSeverity.INFO
    assert log.user_id == test_user.id
    assert log.metadata_json == {"test": "data"}
    
    # Test retrieving the log
    from sqlalchemy import select
    result = await test_db.execute(select(ActivityLog).where(ActivityLog.id == log.id))
    retrieved_log = result.scalar_one_or_none()
    assert retrieved_log is not None
    assert retrieved_log.description == "Test user activity"

@pytest.mark.asyncio
async def test_activity_log_queries(test_db):
    """Test querying activity logs."""
    # Create a test user
    test_user = User(
        username="testuser2",
        email="test2@example.com",
        full_name="Test User 2"
    )
    test_db.add(test_user)
    await test_db.commit()
    await test_db.refresh(test_user)
    
    # Create activity log service
    service = ActivityLogService()
    
    # Create multiple activity logs
    log_data1 = ActivityLogCreate(
        type=ActivityLogType.USER,
        description="User login",
        severity=ActivityLogSeverity.INFO,
        user_id=test_user.id
    )
    
    log_data2 = ActivityLogCreate(
        type=ActivityLogType.CHAT,
        description="Chat started",
        severity=ActivityLogSeverity.INFO,
        user_id=test_user.id
    )
    
    await service.create_activity_log(test_db, log_data1)
    await service.create_activity_log(test_db, log_data2)
    
    # Test getting recent activity
    recent_logs = await service.get_recent_activity(test_db, limit=10)
    assert len(recent_logs) == 2
    
    # Test filtering by type
    user_logs = await service.get_recent_activity(test_db, types=["user"])
    assert len(user_logs) == 1
    assert user_logs[0].type == ActivityLogType.USER
    
    chat_logs = await service.get_recent_activity(test_db, types=["chat"])
    assert len(chat_logs) == 1
    assert chat_logs[0].type == ActivityLogType.CHAT