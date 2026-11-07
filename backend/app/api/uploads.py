from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError, bad_request
from app.services.palette import PaletteError, extract_palette


async def read_image(file: UploadFile) -> bytes:
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)  # never pull more than we'd accept
    if len(data) > limit:
        raise AppError(413, "too_large", f"Image must be under {get_settings().max_upload_mb} MB")
    if not data:
        raise bad_request("empty_file", "That file is empty")
    return data


def palette_or_400(data: bytes) -> list[dict]:
    try:
        return extract_palette(data)
    except PaletteError as exc:
        raise bad_request("bad_image", str(exc))
