"""
Script to create the first admin user for the Agent Hub system.
Run this after initializing the database.
"""
import asyncio
import sys
from getpass import getpass
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database.models import User, UserRole
from app.services.auth_service import AuthService
from app.config.settings import DATABASE_URL


async def create_admin_user():
    """Create the first admin user."""
    print("=== Agent Hub Admin User Setup ===")
    
    # Get admin user details
    full_name = input("Enter admin full name: ").strip()
    if not full_name:
        print("Full name is required!")
        return
    
    email = input("Enter admin email: ").strip()
    if not email or '@' not in email:
        print("Valid email is required!")
        return
    
    password = getpass("Enter admin password: ").strip()
    if len(password) < 8:
        print("Password must be at least 8 characters long!")
        return
    
    confirm_password = getpass("Confirm admin password: ").strip()
    if password != confirm_password:
        print("Passwords do not match!")
        return
    
    # Create database session
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    auth_service = AuthService()
    
    try:
        async with async_session() as session:
            # Check if admin already exists
            existing_admin = await auth_service.get_user_by_email(session, email)
            if existing_admin:
                print(f"User with email {email} already exists!")
                return
            
            # Create admin user
            print("Creating admin user...")
            await auth_service.create_admin_user(
                session, full_name, email, password
            )
            
            print(f"✅ Admin user created successfully!")
            print(f"Email: {email}")
            print(f"Role: ADMIN")
            
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
    finally:
        await engine.dispose()


async def list_admins():
    """List all admin users."""
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    auth_service = AuthService()
    
    try:
        async with async_session() as session:
            admins = await auth_service.get_users_by_role(session, UserRole.ADMIN)
            
            if not admins:
                print("No admin users found.")
            else:
                print("\n=== Current Admin Users ===")
                for admin in admins:
                    print(f"ID: {admin.id}")
                    print(f"Name: {admin.full_name}")
                    print(f"Email: {admin.email}")
                    print(f"Created: {admin.created_at}")
                    print("-" * 30)
                    
    except Exception as e:
        print(f"❌ Failed to list admin users: {e}")
    finally:
        await engine.dispose()


async def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        await list_admins()
    else:
        await create_admin_user()


if __name__ == "__main__":
    asyncio.run(main())
