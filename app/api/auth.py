from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from app.models.user import User, KYCStatus
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.audit import AuditLog
from datetime import datetime
import re

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    username: str
    phone: str = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_token: str = None


class UpdateProfileRequest(BaseModel):
    full_name: str = None
    phone: str = None
    username: str = None


@router.post("/register")
async def register(data: RegisterRequest, request: Request):
    # Check email exists
    if await User.find_one(User.email == data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await User.find_one(User.username == data.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=data.email,
        full_name=data.full_name,
        username=data.username,
        phone=data.phone,
        hashed_password=hash_password(data.password),
    )
    await user.insert()

    await AuditLog(
        user_id=str(user.id),
        action="register",
        resource="user",
        resource_id=str(user.id),
        ip_address=request.client.host,
    ).insert()

    token = create_access_token({"sub": str(user.id)})
    return {
        "token": token,
        "user": _serialize_user(user),
    }


@router.post("/login")
async def login(data: LoginRequest, request: Request):
    user = await User.find_one(User.email == data.email)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account suspended")

    # Update device token
    if data.device_token and data.device_token not in user.device_tokens:
        user.device_tokens.append(data.device_token)

    user.last_seen = datetime.utcnow()
    await user.save()

    await AuditLog(
        user_id=str(user.id),
        action="login",
        resource="user",
        resource_id=str(user.id),
        ip_address=request.client.host,
    ).insert()

    token = create_access_token({"sub": str(user.id)})
    return {
        "token": token,
        "user": _serialize_user(user),
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return _serialize_user(current_user)


@router.put("/me")
async def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user)
):
    if data.full_name:
        current_user.full_name = data.full_name
    if data.phone:
        current_user.phone = data.phone
    if data.username:
        existing = await User.find_one(User.username == data.username)
        if existing and str(existing.id) != str(current_user.id):
            raise HTTPException(status_code=400, detail="Username taken")
        current_user.username = data.username
    current_user.updated_at = datetime.utcnow()
    await current_user.save()
    return _serialize_user(current_user)


def _serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "username": user.username,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "is_verified": user.is_verified,
        "is_admin": user.is_admin,
        "kyc_status": user.kyc_status,
        "trust_score": user.trust_score,
        "total_sessions": user.total_sessions,
        "created_at": user.created_at.isoformat(),
        "last_seen": user.last_seen.isoformat() if user.last_seen else None,
    }
