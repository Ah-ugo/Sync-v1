from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.models.user import User, KYCStatus
from app.models.kyc import KYCSubmission
from app.models.session import SyncSession, SessionStatus
from app.models.video import ConsentVideo
from app.models.confirmation import Confirmation
from app.models.revocation import Revocation
from app.models.notification import Notification, NotificationType
from app.models.audit import AuditLog
from app.core.security import get_admin_user
from datetime import datetime
from beanie.operators import In

router = APIRouter()


class KYCReviewRequest(BaseModel):
    status: str  # approved | rejected
    note: Optional[str] = None


class UserActionRequest(BaseModel):
    action: str  # suspend | activate


@router.get("/stats")
async def get_stats(admin: User = Depends(get_admin_user)):
    total_users = await User.count()
    total_sessions = await SyncSession.count()
    sealed_sessions = await SyncSession.find(SyncSession.status == SessionStatus.SEALED).count()
    revoked_sessions = await SyncSession.find(SyncSession.status == SessionStatus.REVOKED).count()
    pending_kyc = await KYCSubmission.find({"status": "pending"}).count()
    active_sessions = await SyncSession.find(In(SyncSession.status, [
        SessionStatus.ACTIVE, SessionStatus.RECORDING
    ])).count()

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "sealed_sessions": sealed_sessions,
        "revoked_sessions": revoked_sessions,
        "pending_kyc": pending_kyc,
        "active_sessions": active_sessions,
    }


@router.get("/users")
async def list_users(
    page: int = 1,
    limit: int = 20,
    search: str = None,
    admin: User = Depends(get_admin_user),
):
    skip = (page - 1) * limit
    query = {}
    if search:
        query = {
            "$or": [
                {"full_name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"username": {"$regex": search, "$options": "i"}},
            ]
        }
    users = await User.find(query).skip(skip).limit(limit).sort("-created_at").to_list()
    total = await User.find(query).count()
    return {
        "users": [_serialize_user(u) for u in users],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.put("/users/{user_id}/action")
async def user_action(
    user_id: str,
    data: UserActionRequest,
    admin: User = Depends(get_admin_user),
):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.action == "suspend":
        user.is_active = False
    elif data.action == "activate":
        user.is_active = True
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    await user.save()
    await AuditLog(
        user_id=str(admin.id),
        action=data.action,
        resource="user",
        resource_id=user_id,
    ).insert()
    return {"success": True}


@router.get("/kyc")
async def list_kyc(
    status: str = "pending",
    page: int = 1,
    limit: int = 20,
    admin: User = Depends(get_admin_user),
):
    skip = (page - 1) * limit
    submissions = await KYCSubmission.find({"status": status}).skip(skip).limit(limit).sort("-submitted_at").to_list()
    total = await KYCSubmission.find({"status": status}).count()

    user_ids = [s.user_id for s in submissions]
    users = await User.find(In(User.id, user_ids)).to_list()
    user_map = {str(u.id): u for u in users}

    result = []
    for s in submissions:
        user = user_map.get(s.user_id)
        result.append({
            "id": str(s.id),
            "user_id": s.user_id,
            "user_name": user.full_name if user else "Unknown",
            "user_email": user.email if user else "",
            "full_name": s.full_name,
            "id_type": s.id_type,
            "id_number": s.id_number,
            "id_front_url": s.id_front_url,
            "id_back_url": s.id_back_url,
            "selfie_url": s.selfie_url,
            "status": s.status,
            "reviewer_note": s.reviewer_note,
            "submitted_at": s.submitted_at.isoformat(),
            "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
        })
    return {"submissions": result, "total": total, "page": page, "pages": (total + limit - 1) // limit}


@router.put("/kyc/{submission_id}/review")
async def review_kyc(
    submission_id: str,
    data: KYCReviewRequest,
    admin: User = Depends(get_admin_user),
):
    sub = await KYCSubmission.get(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    sub.status = data.status
    sub.reviewer_id = str(admin.id)
    sub.reviewer_note = data.note
    sub.reviewed_at = datetime.utcnow()
    sub.updated_at = datetime.utcnow()
    await sub.save()

    user = await User.get(sub.user_id)
    if user:
        if data.status == "approved":
            user.kyc_status = KYCStatus.APPROVED
            user.is_verified = True
        else:
            user.kyc_status = KYCStatus.REJECTED
        await user.save()

        notif_type = NotificationType.KYC_APPROVED if data.status == "approved" else NotificationType.KYC_REJECTED
        await Notification(
            user_id=str(user.id),
            type=notif_type,
            title="Identity Verification Update",
            body=f"Your KYC has been {data.status}." + (f" Note: {data.note}" if data.note else ""),
            data={"submission_id": submission_id},
        ).insert()

    await AuditLog(
        user_id=str(admin.id),
        action=f"kyc_{data.status}",
        resource="kyc_submission",
        resource_id=submission_id,
    ).insert()

    return {"success": True, "status": data.status}


@router.get("/sessions")
async def list_sessions(
    status: str = None,
    page: int = 1,
    limit: int = 20,
    admin: User = Depends(get_admin_user),
):
    skip = (page - 1) * limit
    query = {}
    if status:
        query["status"] = status
    sessions = await SyncSession.find(query).skip(skip).limit(limit).sort("-created_at").to_list()
    total = await SyncSession.find(query).count()
    return {
        "sessions": [_serialize_session(s) for s in sessions],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/sessions/{session_id}/evidence")
async def admin_get_evidence(session_id: str, admin: User = Depends(get_admin_user)):
    session = await SyncSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Not found")
    videos = await ConsentVideo.find({"session_id": session_id}).to_list()
    confirmations = await Confirmation.find({"session_id": session_id}).to_list()
    revocations = await Revocation.find({"session_id": session_id}).to_list()
    return {
        "session": _serialize_session(session),
        "videos": [{
            "user_id": v.user_id,
            "url": v.video_url,
            "public_id": v.video_public_id,
            "checksum": v.checksum,
            "uploaded_at": v.uploaded_at.isoformat()
        } for v in videos],
        "confirmations": [{"user_id": c.user_id, "confirmed_at": c.confirmed_at.isoformat()} for c in confirmations],
        "revocations": [{"user_id": r.user_id, "reason": r.reason, "revoked_at": r.revoked_at.isoformat()} for r in revocations],
    }


@router.get("/audit-logs")
async def get_audit_logs(page: int = 1, limit: int = 50, admin: User = Depends(get_admin_user)):
    skip = (page - 1) * limit
    logs = await AuditLog.find().skip(skip).limit(limit).sort("-timestamp").to_list()
    total = await AuditLog.count()
    return {
        "logs": [{"id": str(l.id), "user_id": l.user_id, "action": l.action, "resource": l.resource, "resource_id": l.resource_id, "timestamp": l.timestamp.isoformat()} for l in logs],
        "total": total,
    }


def _serialize_user(u: User) -> dict:
    return {
        "id": str(u.id), "email": u.email, "full_name": u.full_name,
        "username": u.username, "is_active": u.is_active, "is_admin": u.is_admin,
        "kyc_status": u.kyc_status, "trust_score": u.trust_score,
        "total_sessions": u.total_sessions, "created_at": u.created_at.isoformat(),
        "last_seen": u.last_seen.isoformat() if u.last_seen else None,
    }


def _serialize_session(s: SyncSession) -> dict:
    return {
        "id": str(s.id), "session_code": s.session_code, "session_type": s.session_type,
        "title": s.title, "status": s.status, "initiator_id": s.initiator_id,
        "participant_ids": s.participant_ids, "session_hash": s.session_hash,
        "created_at": s.created_at.isoformat(),
        "sealed_at": s.sealed_at.isoformat() if s.sealed_at else None,
        "revoked_at": s.revoked_at.isoformat() if s.revoked_at else None,
    }
