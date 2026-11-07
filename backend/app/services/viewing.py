"""Viewing-quality maths + seat recommendations.

Kept deliberately simple and explainable: everything is derived from seat
position and screen geometry, so 'why is F12 good?' always has an answer.
"""

from dataclasses import dataclass
from math import atan2, degrees, exp, hypot

from app.services.layout import EYE_HEIGHT

IDEAL_FOV = 45.0  # horizontal angle the screen should fill (between SMPTE 30 and immersive ~60)


@dataclass(slots=True)
class ViewMetrics:
    distance_m: float
    fov_deg: float
    off_axis_deg: float
    vertical_deg: float
    score: int
    verdict: str


def view_metrics(x: float, y: float, z: float, screen: dict) -> ViewMetrics:
    w = float(screen["width"])
    h = float(screen["height"])
    centre_y = float(screen["bottom"]) + h / 2
    eye_y = y + EYE_HEIGHT

    dist = hypot(x, z)
    fov = degrees(2 * atan2(w / 2, max(dist, 0.1)))
    off_axis = degrees(atan2(abs(x), max(z, 0.1)))
    vertical = degrees(atan2(centre_y - eye_y, max(dist, 0.1)))  # + = looking up

    s_fov = exp(-(((fov - IDEAL_FOV) / 18) ** 2))
    s_axis = max(0.0, 1 - off_axis / 38)
    # small upward tilt is fine, neck strain past ~20 deg, looking down is meh
    if vertical > 0:
        s_vert = max(0.0, 1 - max(0.0, vertical - 6) / 22)
    else:
        s_vert = max(0.0, 1 - abs(vertical) / 30)
    score = round(100 * (0.45 * s_fov + 0.35 * s_axis + 0.20 * s_vert))

    if score >= 85:
        verdict = "Sweet spot"
    elif score >= 70:
        verdict = "Great view"
    elif score >= 55:
        verdict = "Good view"
    elif fov > IDEAL_FOV + 20:
        verdict = "Very close to screen"
    elif off_axis > 25:
        verdict = "Angled side view"
    else:
        verdict = "Distant view"
    return ViewMetrics(round(dist, 2), round(fov, 1), round(off_axis, 1), round(vertical, 1), score, verdict)


@dataclass(slots=True)
class SeatInfo:
    id: str
    row_label: str
    number: int
    block: int
    grid_row: int
    category: str
    price_paise: int
    score: int
    available: bool


def recommend(
    seats: list[SeatInfo],
    group_size: int,
    max_price_per_seat: int | None = None,
    categories: set[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """Best contiguous runs of `group_size` seats in one row/block.

    Falls back to 'same row, split by an aisle' when no clean run exists, so a
    group of 6 on a busy night still gets something sensible.
    """
    pool = [
        s for s in seats
        if s.available
        and (max_price_per_seat is None or s.price_paise <= max_price_per_seat)
        and (not categories or s.category in categories)
    ]
    rows: dict[str, list[SeatInfo]] = {}
    for s in pool:
        rows.setdefault(s.row_label, []).append(s)

    options = []
    for row_label, row_seats in rows.items():
        row_seats.sort(key=lambda s: s.number)
        # contiguous inside a block
        run: list[SeatInfo] = []
        for s in row_seats:
            if run and (s.number != run[-1].number + 1 or s.block != run[-1].block):
                run = []
            run.append(s)
            if len(run) >= group_size:
                window = run[-group_size:]
                options.append(_option(window, together=True))
        # fallback: same row, any gap
        if group_size > 1 and len(row_seats) >= group_size:
            best = sorted(row_seats, key=lambda s: -s.score)[:group_size]
            best.sort(key=lambda s: s.number)
            if best[-1].number - best[0].number + 1 != group_size:
                options.append(_option(best, together=False))

    options.sort(key=lambda o: (-o["together"], -o["score"], o["total_paise"]))
    picked, used = [], set()
    for o in options:
        key = frozenset(o["seat_ids"])
        # don't return 5 near-identical windows from the same row
        if any(len(key & u) > 0 for u in used):
            continue
        picked.append(o)
        used.add(key)
        if len(picked) == limit:
            break
    return picked


def _option(window: list[SeatInfo], together: bool) -> dict:
    avg = sum(s.score for s in window) / len(window)
    spread = max(s.score for s in window) - min(s.score for s in window)
    score = round(avg - spread * 0.15 - (0 if together else 12))
    reasons = []
    if together:
        reasons.append(f"{len(window)} seats side by side" if len(window) > 1 else "Single best seat")
    else:
        reasons.append("Same row, split by an aisle")
    if avg >= 80:
        reasons.append("Centred, ideal screen size")
    elif avg >= 65:
        reasons.append("Comfortable viewing angle")
    return {
        "seat_ids": [s.id for s in window],
        "labels": [f"{s.row_label}{s.number}" for s in window],
        "row": window[0].row_label,
        "category": window[0].category,
        "score": max(0, min(100, score)),
        "together": together,
        "total_paise": sum(s.price_paise for s in window),
        "reasons": reasons,
    }
