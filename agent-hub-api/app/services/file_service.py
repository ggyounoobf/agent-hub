import os
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import File, UserPDFContext, generate_uuid
from app.models.file import FileCreate, FileUpdate
import logging

logger = logging.getLogger(__name__)

class FileService:
    """Service for managing file uploads and storage."""
    
    def __init__(self, upload_directory: str = "uploads"):
        self.upload_directory = upload_directory
        # Create upload directory if it doesn't exist
        os.makedirs(upload_directory, exist_ok=True)
    
    async def create_file(
        self,
        db: AsyncSession,
        file_data: FileCreate,
        user_id: str,
        file_content: bytes
    ) -> File:
        """Create a new file record and save the file content."""
        # Generate unique filename
        file_extension = os.path.splitext(file_data.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(self.upload_directory, unique_filename)
        
        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create file record in database with explicit ID
        db_file = File(
            id=generate_uuid(),  # Explicitly generate the ID
            name=file_data.name,
            path=file_path,
            content_type=file_data.content_type,
            size=file_data.size,
            chat_id=file_data.chat_id,
            query_id=file_data.query_id,
            user_id=user_id
        )
        
        db.add(db_file)
        await db.flush()  # Important: flush to get the ID
        await db.commit()
        await db.refresh(db_file)
        
        return db_file
    
    async def get_file(self, db: AsyncSession, file_id: str, user_id: str) -> Optional[File]:
        """Get a file by ID if it belongs to the user."""
        result = await db.execute(
            select(File).where(File.id == file_id).where(File.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_chat_files(self, db: AsyncSession, chat_id: str, user_id: str) -> List[File]:
        """Get all files associated with a chat."""
        result = await db.execute(
            select(File)
            .where(File.chat_id == chat_id)
            .where(File.user_id == user_id)
            .order_by(File.uploaded_at)
        )
        return result.scalars().all()
    
    async def get_query_files(self, db: AsyncSession, query_id: str, user_id: str) -> List[File]:
        """Get all files associated with a query."""
        result = await db.execute(
            select(File)
            .where(File.query_id == query_id)
            .where(File.user_id == user_id)
            .order_by(File.uploaded_at)
        )
        return result.scalars().all()
    
    async def delete_file(self, db: AsyncSession, file_id: str, user_id: str) -> bool:
        """Delete a file and its database record."""
        result = await db.execute(
            select(File).where(File.id == file_id).where(File.user_id == user_id)
        )
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            return False
        
        # Delete file from disk
        try:
            if os.path.exists(db_file.path):
                os.remove(db_file.path)
        except Exception as e:
            logger.warning(f"Failed to delete file from disk: {e}")
        
        # Delete from database
        await db.delete(db_file)
        await db.commit()
        
        return True
    
    async def save_pdf_context(
        self,
        db: AsyncSession,
        user_id: str,
        file_id: str,
        content: str,
        summary: Optional[str] = None
    ) -> UserPDFContext:
        """Save PDF context for a user."""
        # Check if context already exists
        result = await db.execute(
            select(UserPDFContext)
            .where(UserPDFContext.user_id == user_id)
            .where(UserPDFContext.file_id == file_id)
        )
        pdf_context = result.scalar_one_or_none()
        
        if pdf_context:
            # Update existing context
            pdf_context.content = content
            if summary:
                pdf_context.summary = summary
        else:
            # Create new context
            pdf_context = UserPDFContext(
                id=generate_uuid(),
                user_id=user_id,
                file_id=file_id,
                content=content,
                summary=summary
            )
            db.add(pdf_context)
        
        await db.commit()
        await db.refresh(pdf_context)
        return pdf_context
    
    async def get_user_pdf_contexts(
        self,
        db: AsyncSession,
        user_id: str
    ) -> List[UserPDFContext]:
        """Get all PDF contexts for a user."""
        result = await db.execute(
            select(UserPDFContext)
            .where(UserPDFContext.user_id == user_id)
            .order_by(UserPDFContext.updated_at.desc())
        )
        return result.scalars().all()
    
    async def get_latest_pdf_context(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[UserPDFContext]:
        """Get the most recently updated PDF context for a user."""
        result = await db.execute(
            select(UserPDFContext)
            .where(UserPDFContext.user_id == user_id)
            .order_by(UserPDFContext.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()