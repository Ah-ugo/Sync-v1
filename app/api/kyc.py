from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from app.models.user import User, KYCStatus
from app.models.kyc import KYCSubmission
from app.models.notification import Notification, NotificationType
from app.core.security import get_current_user, get_admin_user
from app.services.cloudinary_service import upload_image
from datetime import datetime

router = APIRouter()


@router.post("/submit")
async def submit_kyc(
    full_name: str = Form(...),
    id_type: str = Form(...),
    id_number: str = Form(...),
    id_front: UploadFile = File(...),
    selfie: UploadFile = File(...),
    id_back: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
):
    if current_user.kyc_status == KYCStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Already verified")

    front_data = await id_front.read()
    front_result = await upload_image(front_data, "sync/kyc", f"{str(current_user.id)}_id_front")

    back_url = back_public_id = None
    if id_back:
        back_data = await id_back.read()
        back_result = await upload_image(back_data, "sync/kyc", f"{str(current_user.id)}_id_back")
        back_url = back_result["url"]
        back_public_id = back_result["public_id"]

    selfie_data = await selfie.read()
    selfie_result = await upload_image(selfie_data, "sync/kyc", f"{str(current_user.id)}_selfie")

    submission = KYCSubmission(
        user_id=str(current_user.id),
        full_name=full_name,
        id_type=id_type,
        id_number=id_number,
        id_front_url=front_result["url"],
        id_front_public_id=front_result["public_id"],
        id_back_url=back_url,
        id_back_public_id=back_public_id,
        selfie_url=selfie_result["url"],
        selfie_public_id=selfie_result["public_id"],
    )
    await submission.insert()

    current_user.kyc_status = KYCStatus.PENDING
    await current_user.save()

    return {"status": "submitted", "submission_id": str(submission.id)}


@router.get("/status")
async def get_kyc_status(current_user: User = Depends(get_current_user)):
    sub = await KYCSubmission.find_one({"user_id": str(current_user.id)})
    return {
        "kyc_status": current_user.kyc_status,
        "submission": {
            "id": str(sub.id),
            "status": sub.status,
            "submitted_at": sub.submitted_at.isoformat(),
            "reviewed_at": sub.reviewed_at.isoformat() if sub.reviewed_at else None,
            "reviewer_note": sub.reviewer_note,
        } if sub else None,
    }
