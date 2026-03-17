import cloudinary
import cloudinary.uploader
from app.core.config import settings
import logging
import hashlib

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


async def upload_image(file_bytes: bytes, folder: str, public_id: str = None) -> dict:
    """Upload an image to Cloudinary"""
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            public_id=public_id,
            resource_type="image",
            quality="auto",
            fetch_format="auto",
        )
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }
    except Exception as e:
        logger.error(f"Cloudinary image upload error: {e}")
        raise


async def upload_video(file_bytes: bytes, folder: str, public_id: str = None) -> dict:
    """Upload a video to Cloudinary"""
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            public_id=public_id,
            resource_type="video",
        )
        checksum = hashlib.sha256(file_bytes).hexdigest()
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "checksum": checksum,
            "duration": result.get("duration"),
            "bytes": result.get("bytes"),
        }
    except Exception as e:
        logger.error(f"Cloudinary video upload error: {e}")
        raise


async def delete_asset(public_id: str, resource_type: str = "image") -> bool:
    """Delete an asset from Cloudinary"""
    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return True
    except Exception as e:
        logger.error(f"Cloudinary delete error: {e}")
        return False
