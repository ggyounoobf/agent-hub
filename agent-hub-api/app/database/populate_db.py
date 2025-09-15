
import asyncio
import random
from faker import Faker
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

from app.database.models import User, Chat, Query, Agent
from app.config.settings import DATABASE_URL
from app.services.auth_service import AuthService
from app.utils.logging import setup_logging

logger = setup_logging(__name__)
fake = Faker()

# Configuration
NUM_USERS = 10
CHATS_PER_USER = 5
QUERIES_PER_CHAT = 10
DAYS_RANGE = 30

async def populate_database():
    """Populate the database with fake data for the last 30 days."""
    logger.info("🚀 Starting database population...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    auth_service = AuthService()

    async with async_session() as session:
        try:
            # Get available agents
            agents_result = await session.execute(select(Agent))
            agents = agents_result.scalars().all()
            # Always use the real agent names from agent_loader.py
            agent_names = ["sample_agent", "github_agent", "pdf_agent", "scraper_agent", "security_agent", "chart_agent", "azure_agent"]
            if agents:
                # Filter to only include agents that actually exist in the database
                existing_agent_names = [agent.name for agent in agents]
                agent_names = [name for name in agent_names if name in existing_agent_names]
                if not agent_names:
                    # Fallback to all defined agent names if none match
                    agent_names = ["sample_agent", "github_agent", "pdf_agent", "scraper_agent", "security_agent"]
            else:
                logger.warning("⚠️ No agents found in the database. Using default agent names.")
                # Use a subset of the most common agents
                agent_names = ["sample_agent", "github_agent", "pdf_agent", "scraper_agent", "security_agent"]

            # --- Create Users ---
            users = []
            for _ in range(NUM_USERS):
                full_name = fake.name()
                email = fake.email()
                password = "password"  # Simple password for all fake users
                
                # Check if user already exists
                existing_user = await session.execute(select(User).where(User.email == email))
                if existing_user.scalar_one_or_none():
                    continue
                    
                try:
                    # Hash password
                    from app.auth.security import get_password_hash
                    password_hash = get_password_hash(password)
                    
                    # Generate username from email
                    username = email.split("@")[0]
                    
                    # Ensure unique username
                    base_username = username
                    counter = 1
                    while True:
                        result = await session.execute(select(User).where(User.username == username))
                        if not result.scalar_one_or_none():
                            break
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    # Create user
                    user = User(
                        username=username,
                        email=email,
                        full_name=full_name,
                        password_hash=password_hash,
                        role="USER",
                        is_active=True
                    )
                    
                    session.add(user)
                    await session.flush()  # Flush to get user ID
                    users.append(user)
                except Exception as e:
                    logger.warning(f"⚠️ Could not create user {email}: {e}")
            
            await session.commit()
            logger.info(f"✅ Created {len(users)} users.")
            logger.info(f"✅ Created {len(users)} users.")

            # --- Create Chats and Queries ---
            for user in users:
                for _ in range(CHATS_PER_USER):
                    chat_created_at = fake.date_time_between(start_date=f"-{DAYS_RANGE}d", end_date="now", tzinfo=timezone.utc)
                    chat = Chat(
                        user_id=user.id,
                        title=fake.sentence(nb_words=4),
                        created_at=chat_created_at,
                        updated_at=chat_created_at
                    )
                    session.add(chat)
                    await session.flush()  # Flush to get chat ID

                    for _ in range(QUERIES_PER_CHAT):
                        query_created_at = fake.date_time_between(start_date=chat_created_at, end_date="now", tzinfo=timezone.utc)
                        query = Query(
                            chat_id=chat.id,
                            message=fake.paragraph(nb_sentences=3),
                            response=fake.paragraph(nb_sentences=5),
                            agent_used=random.choice(agent_names),
                            token_usage={
                                "total_tokens": random.randint(500, 2000),
                                "prompt_tokens": random.randint(100, 500),
                                "completion_tokens": random.randint(400, 1500),
                            },
                            status=random.choices(["completed", "failed", "pending"], weights=[0.8, 0.1, 0.1], k=1)[0],
                            created_at=query_created_at,
                            updated_at=query_created_at
                        )
                        session.add(query)

            await session.commit()
            logger.info("✅ Created chats and queries.")
            logger.info("✅ Database population complete.")

        except Exception as e:
            logger.error(f"❌ Failed to populate database: {e}")
            await session.rollback()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(populate_database())
