"""Turns an authored auditorium layout into concrete seat positions.

Layout format (all lengths in metres):

    {
      "screen": {"width": 14, "height": 6, "curvature": 0.2, "distance": 5.5, "bottom": 1.4},
      "aisle_width": 1.2,
      "arc_focus": 18,          # 0 -> straight rows, else rows bend around a point behind the screen
      "rise_per_row": 0.3,      # stadium step height
      "flat_rows": 2,           # first N rows stay on the floor
      "rows": [
        {"label": "A", "category": "standard", "blocks": [5, 10, 5],
         "blocked": [1], "accessible": [2, 3], "gap_before": 0.0}
      ]
    }

Numbering runs left to right as seen by someone sitting and facing the screen.
"""

from dataclasses import dataclass
from math import cos, sin

from app.models import SeatCategory

# width / row pitch per category - rough real-world numbers
SEAT_SPECS = {
    SeatCategory.standard: {"width": 0.56, "pitch": 1.0},
    SeatCategory.premium: {"width": 0.62, "pitch": 1.1},
    SeatCategory.vip: {"width": 0.78, "pitch": 1.4},
    SeatCategory.recliner: {"width": 0.9, "pitch": 1.7},
}

DEFAULT_SCREEN = {"width": 14.0, "height": 6.0, "curvature": 0.15, "distance": 5.5, "bottom": 1.4}
EYE_HEIGHT = 1.15  # seated eye height above the row floor


@dataclass(slots=True)
class SeatSpec:
    row_label: str
    number: int
    label: str
    category: SeatCategory
    block: int
    x: float
    y: float
    z: float
    yaw: float
    grid_col: int
    grid_row: int
    is_blocked: bool
    is_accessible: bool


class LayoutError(ValueError):
    pass


def normalise_layout(layout: dict) -> dict:
    if not isinstance(layout, dict) or not layout.get("rows"):
        raise LayoutError("layout needs at least one row")
    out = dict(layout)
    out["screen"] = {**DEFAULT_SCREEN, **(layout.get("screen") or {})}
    out.setdefault("aisle_width", 1.2)
    out.setdefault("arc_focus", 0)
    out.setdefault("rise_per_row", 0.3)
    out.setdefault("flat_rows", 1)

    seen = set()
    for row in out["rows"]:
        label = str(row.get("label", "")).strip().upper()
        if not label or len(label) > 3:
            raise LayoutError(f"bad row label {label!r}")
        if label in seen:
            raise LayoutError(f"duplicate row {label}")
        seen.add(label)
        row["label"] = label
        try:
            row["category"] = SeatCategory(row.get("category", "standard")).value
        except ValueError as exc:
            raise LayoutError(f"unknown category in row {label}") from exc
        blocks = row.get("blocks") or []
        if not blocks or any((not isinstance(b, int)) or b < 0 or b > 40 for b in blocks):
            raise LayoutError(f"row {label}: blocks must be small positive ints")
        if sum(blocks) == 0:
            raise LayoutError(f"row {label} has no seats")
    if sum(sum(r["blocks"]) for r in out["rows"]) > 1200:
        raise LayoutError("that is a stadium, not an auditorium (max 1200 seats)")
    return out


def build_seats(layout: dict) -> list[SeatSpec]:
    layout = normalise_layout(layout)
    aisle = float(layout["aisle_width"])
    focus = float(layout["arc_focus"])
    rise = float(layout["rise_per_row"])
    flat_rows = int(layout["flat_rows"])

    # widest row decides the grid width so the 2D map lines up nicely
    def row_units(r):
        return sum(r["blocks"]) + (len(r["blocks"]) - 1)

    max_units = max(row_units(r) for r in layout["rows"])

    seats: list[SeatSpec] = []
    z = float(layout["screen"]["distance"])
    floor = 0.0
    for r_idx, row in enumerate(layout["rows"]):
        cat = SeatCategory(row["category"])
        spec = SEAT_SPECS[cat]
        z += float(row.get("gap_before", 0.0))
        if r_idx > 0:
            prev = SEAT_SPECS[SeatCategory(layout["rows"][r_idx - 1]["category"])]
            z += (prev["pitch"] + spec["pitch"]) / 2
            if r_idx >= flat_rows:
                floor += rise
        blocked = set(row.get("blocked", []))
        accessible = set(row.get("accessible", []))

        n_blocks = len(row["blocks"])
        total_w = sum(row["blocks"]) * spec["width"] + aisle * (n_blocks - 1)
        cursor = -total_w / 2
        col = (max_units - row_units(row)) // 2 + int(row.get("offset", 0))
        number = 1
        for b_idx, count in enumerate(row["blocks"]):
            for _ in range(count):
                x_flat = cursor + spec["width"] / 2
                if focus > 0:
                    radius = z + focus
                    angle = x_flat / radius
                    x, zz, yaw = sin(angle) * radius, cos(angle) * radius - focus, -angle
                else:
                    x, zz, yaw = x_flat, z, 0.0
                seats.append(
                    SeatSpec(
                        row_label=row["label"],
                        number=number,
                        label=f"{row['label']}{number}",
                        category=cat,
                        block=b_idx,
                        x=round(x, 3),
                        y=round(floor, 3),
                        z=round(zz, 3),
                        yaw=round(yaw, 4),
                        grid_col=col,
                        grid_row=r_idx,
                        is_blocked=number in blocked,
                        is_accessible=number in accessible,
                    )
                )
                number += 1
                col += 1
                cursor += spec["width"]
            if b_idx < n_blocks - 1:
                cursor += aisle
                col += 1  # empty grid cell = aisle in the 2D map
    return seats


def layout_summary(layout: dict) -> dict:
    seats = build_seats(layout)
    by_cat: dict[str, int] = {}
    for s in seats:
        by_cat[s.category.value] = by_cat.get(s.category.value, 0) + 1
    depth = max(s.z for s in seats) + 3
    width = max(abs(s.x) for s in seats) * 2 + 4
    return {
        "seat_count": len(seats),
        "rows": len({s.row_label for s in seats}),
        "by_category": by_cat,
        "room": {"width": round(max(width, normalise_layout(layout)["screen"]["width"] + 4), 2), "depth": round(depth, 2),
                 "height": round(max(s.y for s in seats) + 5.5, 2)},
    }
