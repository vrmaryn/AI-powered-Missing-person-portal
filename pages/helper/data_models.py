from uuid import uuid4
from datetime import datetime

from sqlmodel import Field, create_engine, SQLModel
from typing import Optional
from pydantic import validator


class PublicSubmissions(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    # Changed: UUID -> str, uuid4 -> lambda: str(uuid4())
    id: str = Field(
        primary_key=True, default_factory=lambda: str(uuid4()), nullable=False
    )
    submitted_by: Optional[str] = Field(default=None, max_length=128, nullable=True)
    face_mesh: Optional[str] = Field(default=None, nullable=True)        # JSON string
    location: Optional[str] = Field(default=None, max_length=128, nullable=True)
    mobile: str = Field(max_length=10, nullable=False)
    email: Optional[str] = Field(default=None, max_length=64, nullable=True)
    status: str = Field(max_length=16, nullable=False)
    birth_marks: Optional[str] = Field(default=None, max_length=512, nullable=True)
    linked_case_id: Optional[str] = Field(default=None, nullable=True)
    face_embedding: Optional[str] = Field(default=None, nullable=True)   # JSON string
    embedding_model: Optional[str] = Field(default=None, max_length=64, nullable=True)
    embedding_dim: int = Field(default=0, nullable=True)
    embedding_status: str = Field(default="pending", max_length=16, nullable=False)
    submitted_on: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    embedding_created_on: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# Add this validator inside the class to auto-convert "" → None
@validator("face_mesh", "face_embedding", pre=True, always=True)
def empty_json_to_none(cls, v):
    return None if v == "" else v


class RegisteredCases(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    # Changed: UUID -> str, uuid4 -> lambda: str(uuid4())
    id: str = Field(
        primary_key=True, default_factory=lambda: str(uuid4()), nullable=False
    )
    submitted_by: str = Field(max_length=64, nullable=False)
    name: str = Field(max_length=128, nullable=False)
    father_name: str = Field(max_length=128, nullable=True)
    age: str = Field(max_length=8, nullable=True)
    complainant_name: str = Field(max_length=128)
    complainant_mobile: str = Field(max_length=10, nullable=True)
    adhaar_card: str = Field(max_length=12)
    last_seen: str = Field(max_length=64)
    address: str = Field(max_length=512)
    face_mesh: str = Field(nullable=False)  # JSON string of face mesh landmarks
    # Changed: datetime.utcnow() -> datetime.utcnow (remove parentheses)
    submitted_on: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    status: str = Field(max_length=16, nullable=False)
    birth_marks: str = Field(max_length=512)
    matched_with: str = Field(nullable=True)
    face_embedding: str = Field(default="", nullable=True)
    embedding_model: str = Field(default="", max_length=64, nullable=True)
    embedding_dim: int = Field(default=0, nullable=True)
    embedding_status: str = Field(default="pending", max_length=16, nullable=False)
    embedding_created_on: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    
# ADD THIS AFTER RegisteredCases class (around line 70)

class NotificationSubscribers(SQLModel, table=True):
    """Public subscribers who want alerts for their area"""
    __table_args__ = {"extend_existing": True}
    __tablename__ = "notification_subscribers"
    
    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()), nullable=False)
    name: str = Field(max_length=128, nullable=False)
    email: str = Field(max_length=128, nullable=False, unique=True)
    area: str = Field(max_length=64, nullable=False)  # Delhi, Mumbai, etc.
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)