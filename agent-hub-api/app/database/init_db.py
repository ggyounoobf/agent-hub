import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database.connection import Base
from app.config.settings import DATABASE_URL
from app.database.models import User, RefreshToken, Chat, Query, UserRole, File, ActivityLog
from app.utils.logging import setup_logging
from app.services.auth_service import AuthService

logger = setup_logging(__name__)


async def create_tables():
    """Create all database tables."""
    try:
        engine = create_async_engine(DATABASE_URL, echo=True)
        
        async with engine.begin() as conn:
            # Drop all tables (for development)
            await conn.run_sync(Base.metadata.drop_all)
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        await engine.dispose()
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise


async def create_default_admin_user():
    """Create a default admin user with credentials root/password."""
    try:
        engine = create_async_engine(DATABASE_URL)
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        auth_service = AuthService()
        
        async with async_session() as session:
            # Check if admin user already exists
            existing_admin = await auth_service.get_user_by_username(session, "root")
            if existing_admin:
                logger.info("✅ Default admin user already exists")
                return
            
            # Create default admin user
            admin_user = await auth_service.create_admin_user(
                session, 
                "Root Administrator", 
                "root@example.com", 
                "123456789"
            )
            
            logger.info("✅ Default admin user created successfully")
            logger.info("   Username: root")
            logger.info("   Email: root@example.com")
            logger.info("   Password: 123456789")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"❌ Failed to create default admin user: {e}")
        raise


async def init_database():
    """Initialize database with tables and default admin user."""
    await create_tables()
    await create_default_admin_user()


if __name__ == "__main__":
    asyncio.run(init_database())
