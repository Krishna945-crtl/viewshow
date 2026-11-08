import io
import struct
import zlib

import pytest
from PIL import Image

from app.services.palette import PaletteError, extract_palette, image_format


def poster(*bands, size=(60, 90), fmt="PNG") -> bytes:
    """Fake poster made of horizontal colour bands: poster(("#ff3fa4", 3), ("#101018", 1))."""
    im = Image.new("RGB", size)
    total = sum(n for _, n in bands)
    y = 0
    for colour, n in bands:
        h = round(size[1] * n / total)
        im.paste(colour, (0, y, size[0], y + h))
        y += h
    buf = io.BytesIO()
    im.save(buf, fmt)
    return buf.getvalue()


def test_dominant_colours_come_out_in_order():
    pal = extract_palette(poster(("#ff3fa4", 6), ("#101018", 3), ("#7ee8fa", 1)))
    assert [p["hex"] for p in pal[:3]] == ["#ff3fa4", "#101018", "#7ee8fa"]
    assert abs(pal[0]["weight"] - 0.6) < 0.05
    assert abs(sum(p["weight"] for p in pal) - 1) < 0.02


def test_near_duplicates_are_merged():
    pal = extract_palette(poster(("#204080", 1), ("#224284", 1), ("#f0c040", 1)))
    assert len(pal) == 2


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
def test_other_formats(fmt):
    pal = extract_palette(poster(("#1e6fd9", 1), size=(40, 40), fmt=fmt))
    r, g, b = (int(pal[0]["hex"][i:i + 2], 16) for i in (1, 3, 5))
    assert b > 180 and r < 70  # lossy, but clearly the same blue
    assert image_format(poster(("#000000", 1), fmt=fmt)) == fmt


def test_rejects_non_images_and_gifs():
    with pytest.raises(PaletteError):
        extract_palette(b"definitely not an image")
    with pytest.raises(PaletteError):
        extract_palette(poster(("#ff0000", 1), fmt="GIF"))
    with pytest.raises(PaletteError):
        extract_palette(b"")


def test_rejects_decompression_bombs():
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    # header claims 30000x30000 - must be refused before anything is decoded
    bomb = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 30000, 30000, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00" * 10)) + chunk(b"IEND", b""))
    with pytest.raises(PaletteError, match="too large"):
        extract_palette(bomb)
