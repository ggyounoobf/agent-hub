import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.connection import DATABASE_URL
from app.database.models import File, User
from app.services.file_service import FileService
from app.models.file import FileCreate

async def test_file_service():
    """Test the file service to see if it's working correctly."""
    # Create engine and session
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create file service
    file_service = FileService()
    
    # Create a test user (we'll need to get an actual user ID from the database)
    async with async_session() as session:
        # Get the first user from the database
        result = await session.execute("SELECT id FROM users LIMIT 1")
        user_row = result.fetchone()
        
        if not user_row:
            print("No users found in database")
            return
            
        user_id = user_row[0]
        print(f"Using user ID: {user_id}")
        
        # Create a test file
        test_content = b"This is a test PDF file content"
        file_create = FileCreate(
            name="test_file.pdf",
            content_type="application/pdf",
            size=len(test_content)
        )
        
        try:
            # Test creating a file
            file_record = await file_service.create_file(
                session, file_create, user_id, test_content
            )
            
            print(f"Successfully created file:")
            print(f"  ID: {file_record.id}")
            print(f"  Name: {file_record.name}")
            print(f"  Path: {file_record.path}")
            print(f"  Size: {file_record.size}")
            
            # Check if file exists on disk
            if os.path.exists(file_record.path):
                print(f"File exists on disk: {file_record.path}")
                # Read the file back
                with open(file_record.path, "rb") as f:
                    content = f.read()
                    print(f"File content matches: {content == test_content}")
            else:
                print(f"File does not exist on disk: {file_record.path}")
                
            # Test retrieving the file
            retrieved_file = await file_service.get_file(session, file_record.id, user_id)
            if retrieved_file:
                print(f"Successfully retrieved file: {retrieved_file.name}")
            else:
                print("Failed to retrieve file")
                
            # Test updating file processing status
            updated_file = await file_service.update_file_processing_status(
                session,
                file_record.id,
                extracted_text="This is the extracted text",
                summary="This is a test summary",
                word_count=5,
                page_count=1
            )
            
            if updated_file:
                print(f"Successfully updated file processing status")
                print(f"  Extracted text: {updated_file.extracted_text[:50]}...")
                print(f"  Summary: {updated_file.summary}")
                print(f"  Word count: {updated_file.word_count}")
                print(f"  Page count: {updated_file.page_count}")
                print(f"  Processed: {updated_file.is_processed}")
            else:
                print("Failed to update file processing status")
                
            # Test deleting the file
            delete_result = await file_service.delete_file(session, file_record.id, user_id)
            if delete_result:
                print("Successfully deleted file")
            else:
                print("Failed to delete file")
                
        except Exception as e:
            print(f"Error during file service test: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_file_service())