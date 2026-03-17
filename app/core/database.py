from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = None


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    
    from app.models.user import User
    from app.models.kyc import KYCSubmission
    from app.models.session import SyncSession
    from app.models.participant import SessionParticipant
    from app.models.video import ConsentVideo
    from app.models.confirmation import Confirmation
    from app.models.revocation import Revocation
    from app.models.notification import Notification
    from app.models.audit import AuditLog

    await init_beanie(
        database=client[settings.DATABASE_NAME],
        document_models=[
            User, KYCSubmission, SyncSession, SessionParticipant,
            ConsentVideo, Confirmation, Revocation, Notification, AuditLog
        ]
    )
    logger.info("✅ MongoDB connected")


async def close_db():
    global client
    if client:
        client.close()
        logger.info("❌ MongoDB disconnected")
