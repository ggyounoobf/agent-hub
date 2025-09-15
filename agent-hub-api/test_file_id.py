import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database.connection import DATABASE_URL, get_db_session
from app.database.models import File
from app.models.file import FileCreate
from app.services.file_service import FileService

async def test_file_creation():
    """Test if file records are being created with IDs."""
    # Get database session
    db_gen = get_db_session()
    db = await db_gen.__anext__()
    
    try:
        file_service = FileService()
        
        # Create a test file record
        file_create = FileCreate(
            name="test.pdf",
            content_type="application/pdf",
            size=1024
        )
        
        # Save file
        file_record = await file_service.create_file(
            db, file_create, "test-user-id", b"test content"
        )
        
        print(f"File created successfully:")
        print(f"  ID: {file_record.id}")
        print(f"  Name: {file_record.name}")
        print(f"  Path: {file_record.path}")
        
        # Test the metadata processing
        from app.services.chat_service import ChatService
        chat_service = ChatService()
        metadata = chat_service._process_file_records_metadata([file_record])
        print(f"Processed metadata: {metadata}")
        
        # Clean up
        await file_service.delete_file(db, file_record.id, "test-user-id")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_gen.aclose()

if __name__ == "__main__":
    asyncio.run(test_file_creation())