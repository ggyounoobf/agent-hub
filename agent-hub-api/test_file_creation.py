import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.connection import DATABASE_URL, get_db_session
from app.database.models import File
from app.models.file import FileCreate

async def test_file_creation():
    """Test creating a file record in the database."""
    # Get database session
    db_gen = get_db_session()
    db = await db_gen.__anext__()
    
    try:
        # Create a test file record
        test_file = File(
            name="test.pdf",
            path="/tmp/test.pdf",
            content_type="application/pdf",
            size=1024,
            user_id="test-user-id"
        )
        
        # Add to database
        db.add(test_file)
        await db.commit()
        await db.refresh(test_file)
        
        print(f"Successfully created file record:")
        print(f"  ID: {test_file.id}")
        print(f"  Name: {test_file.name}")
        print(f"  Path: {test_file.path}")
        print(f"  Size: {test_file.size}")
        print(f"  User ID: {test_file.user_id}")
        print(f"  Uploaded at: {test_file.uploaded_at}")
        
        # Clean up - delete the test record
        await db.delete(test_file)
        await db.commit()
        print("Test record cleaned up successfully")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_gen.aclose()

if __name__ == "__main__":
    asyncio.run(test_file_creation())