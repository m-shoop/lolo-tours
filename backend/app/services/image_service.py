"""Image upload validation and storage helpers."""
from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import settings

_ALLOWED_FORMATS = {"JPEG", "PNG"}
_FORMAT_TO_EXT = {"JPEG": ".jpg", "PNG": ".png"}
_TOUR_IMAGES_SUBDIR = "tour-images"


def _tour_images_dir() -> Path:
    path = Path(settings.upload_dir) / _TOUR_IMAGES_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


async def validate_and_store_image(upload: UploadFile) -> str:
    """Validate (size + Pillow), persist to disk under a UUID filename.

    Returns the filename (basename only — caller stores in DB and clients reach
    it via settings.image_url_prefix).
    """
    contents = await upload.read()

    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_bytes} bytes",
        )
    if len(contents) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    try:
        with Image.open(io.BytesIO(contents)) as img:
            img.verify()
            fmt = img.format
    except (UnidentifiedImageError, Exception):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not parse file as an image",
        )

    if fmt not in _ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only PNG and JPEG accepted (got {fmt})",
        )

    filename = f"{uuid.uuid4().hex}{_FORMAT_TO_EXT[fmt]}"
    dest = _tour_images_dir() / filename
    dest.write_bytes(contents)
    return filename


def delete_image_file(filename: str) -> None:
    """Best-effort delete; missing files are silently ignored."""
    if not filename:
        return
    path = _tour_images_dir() / filename
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def public_url(filename: str) -> str:
    return f"{settings.image_url_prefix}/{filename}"
