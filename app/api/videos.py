from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from app.models.user import User
from app.models.session import SyncSession, SessionStatus
from app.models.video import ConsentVideo
from app.models.notification import Notification, NotificationType
from app.core.security import get_current_user
from app.services.cloudinary_service import upload_video
from app.services.websocket_manager import manager

router = APIRouter()


@router.post("/upload")
async def upload_consent_video(
    session_id: str = Form(...),
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    session = await SyncSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(current_user.id) not in session.participant_ids:
        raise HTTPException(status_code=403, detail="Not a participant")
    if session.status not in [SessionStatus.RECORDING, SessionStatus.ACTIVE]:
        raise HTTPException(status_code=400, detail="Session not in recording state")

    video_data = await video.read()
    result = await upload_video(
        video_data,
        "sync/consent_videos",
        f"{session_id}_{str(current_user.id)}"
    )

    consent_video = ConsentVideo(
        session_id=session_id,
        user_id=str(current_user.id),
        video_url=result["url"],
        video_public_id=result["public_id"],
        checksum=result["checksum"],
        duration_seconds=result.get("duration"),
        file_size_bytes=result.get("bytes"),
    )
    await consent_video.insert()

    if session.status == SessionStatus.RECORDING:
        session.status = SessionStatus.AWAITING_CONFIRMATION
        await session.save()

    await manager.broadcast_to_session(session_id, "video_uploaded", {
        "session_id": session_id,
        "user_id": str(current_user.id),
        "username": current_user.username,
    })

    return {
        "video_id": str(consent_video.id),
        "url": consent_video.video_url,
        "checksum": consent_video.checksum,
    }
