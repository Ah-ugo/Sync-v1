from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    SESSION_INVITE = "session_invite"
    SESSION_JOINED = "session_joined"
    VIDEO_UPLOADED = "video_uploaded"
    CONSENT_CONFIRMED = "consent_confirmed"
    CONSENT_REVOKED = "consent_revoked"
    SESSION_SEALED = "session_sealed"
    KYC_APPROVED = "kyc_approved"
    KYC_REJECTED = "kyc_rejected"

class Notification(Document):
    user_id: str
    type: NotificationType
    title: str
    body: str
    data: dict = {}
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "notifications"
