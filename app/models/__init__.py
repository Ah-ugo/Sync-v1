from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SessionParticipant(Document):
    session_id: str
    user_id: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    device_fingerprint: Optional[str] = None

    class Settings:
        name = "session_participants"


class ConsentVideo(Document):
    session_id: str
    user_id: str
    video_url: str
    video_public_id: str
    checksum: str
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "consent_videos"


class Confirmation(Document):
    session_id: str
    user_id: str
    confirmed_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    device_info: Optional[str] = None

    class Settings:
        name = "confirmations"


class RevocationReason(str, Enum):
    CHANGED_MIND = "changed_mind"
    UNCOMFORTABLE = "uncomfortable"
    EMERGENCY = "emergency"
    TECHNICAL = "technical"
    OTHER = "other"


class Revocation(Document):
    session_id: str
    user_id: str
    reason: RevocationReason = RevocationReason.OTHER
    note: Optional[str] = None
    revoked_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None

    class Settings:
        name = "revocations"


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


class AuditLog(Document):
    user_id: Optional[str] = None
    action: str
    resource: str
    resource_id: Optional[str] = None
    details: dict = {}
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_logs"
