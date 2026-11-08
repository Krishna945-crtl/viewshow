"""Pull the dominant colours out of a poster / key-art image.

Only hex colours + their share of the image are kept. Colours aren't anyone's
property, so a theme built from them never depends on the artwork itself -
the image can be thrown away right after this runs.
"""

from __future__ import annotations

import io
import warnings

from PIL import Image

ALLOWED = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000  # a 6000x6000 poster is fine, a decompression bomb is not
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class PaletteError(ValueError):
    pass


def _hex(rgb) -> str:
    return "#" + "".join(f"{c:02x}" for c in rgb)


def _close(a, b, limit=34) -> bool:
    # plain RGB distance is fine at this scale; we're grouping, not grading colour
    return sum((x - y) ** 2 for x, y in zip(a, b)) < limit ** 2


def image_format(data: bytes) -> str | None:
    """'JPEG' / 'PNG' / 'WEBP' from the header only - no full decode."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            return im.format if im.format in ALLOWED else None
    except Exception:
        return None


def extract_palette(data: bytes, colours: int = 6) -> list[dict]:
    """[{"hex": "#d4572a", "weight": 0.31}, ...] sorted by how much of the image it covers."""
    if not data:
        raise PaletteError("empty file")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:
                if im.format not in ALLOWED:
                    raise PaletteError("use a JPEG, PNG or WebP image")
                im.draft("RGB", (320, 320))  # jpeg decoder can skip most of the work
                small = im.convert("RGB")
    except PaletteError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise PaletteError("image is too large")
    except Exception as exc:  # truncated / not an image at all
        raise PaletteError("could not read that image") from exc

    small.thumbnail((128, 128))
    q = small.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette() or []
    counts = sorted(q.getcolors() or [], reverse=True)
    total = sum(c for c, _ in counts) or 1

    merged: list[list] = []  # [rgb, count]
    for count, idx in counts:
        rgb = tuple(pal[idx * 3: idx * 3 + 3])
        for m in merged:
            if _close(m[0], rgb):
                # weighted average so the swatch drifts towards the bigger area
                n = m[1] + count
                m[0] = tuple(round((a * m[1] + b * count) / n) for a, b in zip(m[0], rgb))
                m[1] = n
                break
        else:
            merged.append([rgb, count])

    merged.sort(key=lambda m: -m[1])
    return [{"hex": _hex(rgb), "weight": round(n / total, 3)} for rgb, n in merged[:colours]]
