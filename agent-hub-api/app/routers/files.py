from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi import File as FastAPIFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import select
import os

from app.database.connection import get_db_session
from app.auth.dependencies import get_current_user
from app.database.models import User, File, UserPDFContext
from app.models.file import FileResponse, FileListResponse, PDFContextResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])
file_service = FileService()


@router.get("/", response_model=List[FileListResponse])
async def list_files(
    chat_id: Optional[str] = None,
    query_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List files for the current user, optionally filtered by chat or query."""
    if chat_id:
        files = await file_service.get_chat_files(db, chat_id, current_user.id)
    elif query_id:
        files = await file_service.get_query_files(db, query_id, current_user.id)
    else:
        # Get all user files
        result = await db.execute(
            select(File)
            .where(File.user_id == current_user.id)
            .order_by(File.uploaded_at.desc())
        )
        files = result.scalars().all()
    
    return files


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get file details."""
    file = await file_service.get_file(db, file_id, current_user.id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    return file


@router.get("/{file_id}/content")
async def get_file_content(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the content of a file for preview."""
    file = await file_service.get_file(db, file_id, current_user.id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if file exists on disk
    if not os.path.exists(file.path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File content not found"
        )
    
    # Return file content
    with open(file.path, "rb") as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type=file.content_type,
        headers={"Content-Disposition": f"inline; filename={file.name}"}
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Download a file."""
    file = await file_service.get_file(db, file_id, current_user.id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if file exists on disk
    if not os.path.exists(file.path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File content not found"
        )
    
    # Return file content as download
    with open(file.path, "rb") as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type=file.content_type,
        headers={"Content-Disposition": f"attachment; filename={file.name}"}
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a file."""
    success = await file_service.delete_file(db, file_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return {"message": "File deleted successfully"}


@router.get("/{file_id}/pdf-context", response_model=PDFContextResponse)
async def get_pdf_context(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the PDF context for a file."""
    # First verify the file exists and belongs to the user
    file = await file_service.get_file(db, file_id, current_user.id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Get the PDF context
    result = await db.execute(
        select(UserPDFContext)
        .where(UserPDFContext.file_id == file_id)
        .where(UserPDFContext.user_id == current_user.id)
    )
    pdf_context = result.scalar_one_or_none()
    
    if not pdf_context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF context not found"
        )
    
    return pdf_context


@router.get("/pdf-context/latest", response_model=PDFContextResponse)
async def get_latest_pdf_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get the latest PDF context for the user."""
    pdf_context = await file_service.get_latest_pdf_context(db, current_user.id)
    
    if not pdf_context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No PDF context found"
        )
    
    return pdf_context
