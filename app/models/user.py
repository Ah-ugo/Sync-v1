from beanie import Document, Indexed
from pydantic import EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class KYCStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Document):
    email: Indexed(EmailStr, unique=True)
    phone: Optional[str] = None
    full_name: str
    username: Indexed(str, unique=True)
    hashed_password: str
    avatar_url: Optional[str] = None
    avatar_public_id: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    is_verified: bool = False
    kyc_status: KYCStatus = KYCStatus.NOT_SUBMITTED
    device_tokens: list[str] = []
    total_sessions: int = 0
    trust_score: float = 100.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None

    class Settings:
        name = "users"
