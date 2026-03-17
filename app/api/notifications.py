from fastapi import APIRouter, Depends
from app.models.user import User
from app.models.notification import Notification
from app.core.security import get_current_user

router = APIRouter()


@router.get("/")
async def get_notifications(
    page: int = 1,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * limit
    notifs = await Notification.find(
        {"user_id": str(current_user.id)}
    ).skip(skip).limit(limit).sort("-created_at").to_list()
    unread = await Notification.find(
        {"user_id": str(current_user.id), "is_read": False}
    ).count()
    return {
        "notifications": [
            {
                "id": str(n.id), "type": n.type, "title": n.title,
                "body": n.body, "data": n.data, "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifs
        ],
        "unread_count": unread,
    }


@router.put("/{notif_id}/read")
async def mark_read(notif_id: str, current_user: User = Depends(get_current_user)):
    n = await Notification.get(notif_id)
    if n and n.user_id == str(current_user.id):
        n.is_read = True
        await n.save()
    return {"success": True}


@router.put("/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    await Notification.find(
        {"user_id": str(current_user.id), "is_read": False}
    ).update({"$set": {"is_read": True}})
    return {"success": True}
