from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FileBase(BaseModel):
    name: str
    content_type: str
    size: int
    chat_id: Optional[str] = None
    query_id: Optional[str] = None


class FileCreate(FileBase):
    pass


class FileUpdate(BaseModel):
    name: Optional[str] = None


class FileResponse(FileBase):
    id: str
    path: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    is_processed: bool = False
    extracted_text: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    id: str
    name: str
    content_type: str
    size: int
    uploaded_at: datetime
    is_processed: bool

    class Config:
        from_attributes = True


class PDFContextResponse(BaseModel):
    file_id: str
    content: str
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True