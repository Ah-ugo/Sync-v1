from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime

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
