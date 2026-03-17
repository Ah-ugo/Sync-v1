from beanie import Document, Indexed
from pydantic import Field
from typing import Optional
from datetime import datetime
from enum import Enum


class KYCStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class KYCSubmission(Document):
    user_id: str
    full_name: str
    id_type: str  # national_id, passport, drivers_license
    id_number: str
    id_front_url: str
    id_front_public_id: str
    id_back_url: Optional[str] = None
    id_back_public_id: Optional[str] = None
    selfie_url: str
    selfie_public_id: str
    status: KYCStatus = KYCStatus.PENDING
    reviewer_id: Optional[str] = None
    reviewer_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "kyc_submissions"
