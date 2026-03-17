from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from app.models.user import User
from app.models.session import SyncSession, SessionStatus, SessionType
from app.models.participant import SessionParticipant
from app.models.confirmation import Confirmation
from app.models.revocation import Revocation, RevocationReason
from app.models.video import ConsentVideo
from app.models.notification import Notification, NotificationType
from app.models.audit import AuditLog
from app.core.security import get_current_user
from app.services.websocket_manager import manager
from app.services.evidence_service import generate_session_hash
from datetime import datetime, timedelta
import secrets

router = APIRouter()


class CreateSessionRequest(BaseModel):
    session_type: SessionType
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class JoinSessionRequest(BaseModel):
    session_code: str


class RevokeSessionRequest(BaseModel):
    reason: RevocationReason = RevocationReason.OTHER
    note: Optional[str] = None


@router.post("/")
async def create_session(
    data: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
):
    code = SyncSession.generate_code()
    while await SyncSession.find_one(SyncSession.session_code == code):
        code = SyncSession.generate_code()

    session = SyncSession(
        session_code=code,
        session_type=data.session_type,
        title=data.title,
        description=data.description,
        location=data.location,
        initiator_id=str(current_user.id),
        participant_ids=[str(current_user.id)],
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    await session.insert()

    await SessionParticipant(
        session_id=str(session.id),
        user_id=str(current_user.id),
    ).insert()

    return _serialize_session(session)


@router.post("/join")
async def join_session(
    data: JoinSessionRequest,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    session = await SyncSession.find_one(SyncSession.session_code == data.session_code)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in [SessionStatus.PENDING]:
        raise HTTPException(status_code=400, detail=f"Cannot join session in {session.status} state")
    if str(current_user.id) in session.participant_ids:
        raise HTTPException(status_code=400, detail="Already in session")

    session.participant_ids.append(str(current_user.id))
    session.status = SessionStatus.ACTIVE
    session.updated_at = datetime.utcnow()
    await session.save()

    await SessionParticipant(
        session_id=str(session.id),
        user_id=str(current_user.id),
        ip_address=request.client.host if request else None,
    ).insert()

    # Notify initiator
    await manager.broadcast_to_session(str(session.id), "session_join", {
        "session_id": str(session.id),
        "user_id": str(current_user.id),
        "username": current_user.username,
    })

    await Notification(
        user_id=session.initiator_id,
        type=NotificationType.SESSION_JOINED,
        title="Someone joined your session",
        body=f"{current_user.full_name} joined your Sync session",
        data={"session_id": str(session.id)},
    ).insert()

    return _serialize_session(session)


@router.get("/")
async def get_my_sessions(current_user: User = Depends(get_current_user)):
    sessions = await SyncSession.find(
        {"participant_ids": str(current_user.id)}
    ).sort("-created_at").to_list()
    return [_serialize_session(s) for s in sessions]


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    session = await SyncSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(current_user.id) not in session.participant_ids and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return _serialize_session(session)


@router.post("/{session_id}/start-recording")
async def start_recording(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    session = await SyncSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session not active")
    if str(current_user.id) not in session.participant_ids:
        raise HTTPException(status_code=403, detail="Not a participant")

    session.status = SessionStatus.RECORDING
    session.updated_at = datetime.utcnow()
    await session.save()

    await manager.broadcast_to_session(session_id, "recording_started", {
        "session_id": session_id,
        "started_by": str(current_user.id),
    })
    return {"status": "recording"}


@router.post("/{session_id}/confirm")
async def confirm_consent(
    session_id: str,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    session = await SyncSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(current_user.id) not in session.participant_ids:
        raise HTTPException(status_code=403, detail="Not a participant")

    # Check not already confirmed
    existing = await Confirmation.find_one({
        "session_id": session_id,
        "user_id": str(current_user.id),
    })
    if existing:
        raise HTTPException(status_code=400, detail="Already confirmed")

    await Confirmation(
        session_id=session_id,
        user_id=str(current_user.id),
        ip_address=request.client.host if request else None,
    ).insert()

    # Check if all confirmed
    confirmations = await Confirmation.find({"session_id": session_id}).to_list()
    all_confirmed = len(confirmations) >= len(session.participant_ids)

    if all_confirmed:
        # Seal the session
        videos = await ConsentVideo.find({"session_id": session_id}).to_list()
        video_checksums = [v.checksum for v in videos]
        conf_timestamps = [str(c.confirmed_at) for c in confirmations]
        sealed_at = datetime.utcnow().isoformat()

        session_hash = generate_session_hash(
            session_id=session_id,
            participant_ids=session.participant_ids,
            video_checksums=video_checksums,
            confirmation_timestamps=conf_timestamps,
            sealed_at=sealed_at,
        )
        session.status = SessionStatus.SEALED
        session.session_hash = session_hash
        session.sealed_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        await session.save()

        # Update user session counts
        for uid in session.participant_ids:
            user = await User.get(uid)
            if user:
                user.total_sessions += 1
                await user.save()

        await manager.broadcast_to_session(session_id, "session_sealed", {
            "session_id": session_id,
            "hash": session_hash,
            "sealed_at": sealed_at,
        })
    else:
        session.status = SessionStatus.AWAITING_CONFIRMATION
        await session.save()
        await manager.broadcast_to_session(session_id, "consent_confirmed", {
            "session_id": session_id,
            "user_id": str(current_user.id),
            "confirmed_count": len(confirmations),
            "total": len(session.participant_ids),
        })

    return {"confirmed": True, "sealed": all_confirmed}


@router.post("/{session_id}/revoke")
async def revoke_session(
    session_id: str,
    data: RevokeSessionRequest,
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    session = await SyncSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(current_user.id) not in session.participant_ids:
        raise HTTPException(status_code=403, detail="Not a participant")
    if session.status in [SessionStatus.SEALED, SessionStatus.REVOKED]:
        raise HTTPException(status_code=400, detail=f"Cannot revoke in {session.status} state")

    await Revocation(
        session_id=session_id,
        user_id=str(current_user.id),
        reason=data.reason,
        note=data.note,
    ).insert()

    session.status = SessionStatus.REVOKED
    session.revoked_at = datetime.utcnow()
    session.revoked_by = str(current_user.id)
    session.revocation_reason = data.reason
    session.updated_at = datetime.utcnow()
    await session.save()

    await manager.broadcast_to_session(session_id, "consent_revoked", {
        "session_id": session_id,
        "revoked_by": str(current_user.id),
        "reason": data.reason,
    })

    return {"revoked": True}


@router.get("/{session_id}/evidence")
async def get_evidence(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    session = await SyncSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Not found")
    if str(current_user.id) not in session.participant_ids and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    videos = await ConsentVideo.find({"session_id": session_id}).to_list()
    confirmations = await Confirmation.find({"session_id": session_id}).to_list()
    revocations = await Revocation.find({"session_id": session_id}).to_list()

    return {
        "session": _serialize_session(session),
        "videos": [{"user_id": v.user_id, "url": v.video_url, "checksum": v.checksum, "uploaded_at": v.uploaded_at.isoformat()} for v in videos],
        "confirmations": [{"user_id": c.user_id, "confirmed_at": c.confirmed_at.isoformat()} for c in confirmations],
        "revocations": [{"user_id": r.user_id, "reason": r.reason, "revoked_at": r.revoked_at.isoformat()} for r in revocations],
    }


def _serialize_session(session: SyncSession) -> dict:
    return {
        "id": str(session.id),
        "session_code": session.session_code,
        "session_type": session.session_type,
        "title": session.title,
        "description": session.description,
        "initiator_id": session.initiator_id,
        "participant_ids": session.participant_ids,
        "status": session.status,
        "location": session.location,
        "session_hash": session.session_hash,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "sealed_at": session.sealed_at.isoformat() if session.sealed_at else None,
        "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
        "revoked_by": session.revoked_by,
    }
