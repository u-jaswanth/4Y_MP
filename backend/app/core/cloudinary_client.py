"""
Optional Cloudinary file storage.

Ported over from the earlier prototype (app.zip's app/core/cloudinary.py)
and made non-fatal: MediConnect can run entirely on local disk storage
(the original behaviour), and will additionally mirror uploads to
Cloudinary whenever CLOUDINARY_* credentials are configured.
"""

import cloudinary
import cloudinary.uploader

from app.config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_ENABLED,
)

if CLOUDINARY_ENABLED:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_file(file_bytes: bytes, folder: str) -> dict | None:
    """
    Uploads raw bytes to Cloudinary and returns
    {"secure_url": ..., "public_id": ...}, or None if Cloudinary
    isn't configured or the upload fails. Never raises - callers
    treat cloud storage as a best-effort mirror of the local copy,
    not a hard dependency.
    """

    if not CLOUDINARY_ENABLED:
        return None

    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            resource_type="auto",
        )

        return {
            "secure_url": result.get("secure_url"),
            "public_id": result.get("public_id"),
        }

    except Exception as error:  # noqa: BLE001
        print(f"[cloudinary] Upload failed, keeping local copy only: {error}")
        return None
