from beanie import Document, Indexed
from pydantic import Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import secrets


class SessionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    RECORDING = "recording"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SEALED = "sealed"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SessionType(str, Enum):
    DATING = "dating"
    MEETING = "meeting"
    TRANSACTION = "transaction"
    BUSINESS = "business"
    CONFLICT = "conflict"
    DELIVERY = "delivery"
    PROPERTY = "property"


class SyncSession(Document):
    session_code: Indexed(str, unique=True)
    session_type: SessionType
    title: Optional[str] = None
    description: Optional[str] = None
    initiator_id: str
    participant_ids: List[str] = []
    status: SessionStatus = SessionStatus.PENDING
    location: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    session_hash: Optional[str] = None
    evidence_sealed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sealed_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    revocation_reason: Optional[str] = None

    class Settings:
        name = "sessions"

    @classmethod
    def generate_code(cls) -> str:
        return secrets.token_hex(3).upper()
