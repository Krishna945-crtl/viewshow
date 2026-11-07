"""Object storage for authorised artwork.

Local disk by default (served at /media). Swap `LocalStorage` for an S3/R2/GCS
class with the same `save`/`delete` methods in production - nothing else changes.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

PUBLIC_PREFIX = "/media"
EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class LocalStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, folder: str, data: bytes, ext: str) -> str:
        d = self.root / folder
        d.mkdir(parents=True, exist_ok=True)
        name = f"{secrets.token_hex(10)}.{ext}"
        (d / name).write_bytes(data)
        return f"{PUBLIC_PREFIX}/{folder}/{name}"

    def delete(self, url: str | None) -> None:
        if not url or not url.startswith(PUBLIC_PREFIX + "/"):
            return  # not ours (external https url) - leave it alone
        p = (self.root / url[len(PUBLIC_PREFIX) + 1:]).resolve()
        if p.is_relative_to(self.root) and p.is_file():
            p.unlink()


@lru_cache
def get_storage() -> LocalStorage:
    return LocalStorage(get_settings().media_dir)
