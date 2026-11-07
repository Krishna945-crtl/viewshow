import pytest

from app.models import SeatCategory
from app.services.layout import LayoutError, build_seats, layout_summary

BASIC = {"screen": {"width": 10}, "aisle_width": 1.0, "rows": [
    {"label": "A", "category": "standard", "blocks": [2, 4, 2]},
    {"label": "b", "category": "recliner", "blocks": [1, 2, 1], "blocked": [1], "accessible": [4]},
]}


def test_counts_and_labels():
    seats = build_seats(BASIC)
    assert len(seats) == 12
    assert [s.label for s in seats if s.row_label == "A"] == [f"A{i}" for i in range(1, 9)]
    b = [s for s in seats if s.row_label == "B"]
    assert b[0].is_blocked and b[-1].is_accessible
    assert all(s.category == SeatCategory.recliner for s in b)


def test_numbering_runs_left_to_right_and_aisles_leave_grid_gaps():
    row_a = [s for s in build_seats(BASIC) if s.row_label == "A"]
    xs = [s.x for s in row_a]
    assert xs == sorted(xs)
    cols = [s.grid_col for s in row_a]
    # 2 seats, gap, 4 seats, gap, 2 seats
    assert cols[2] - cols[1] == 2 and cols[6] - cols[5] == 2


def test_rows_step_up_and_back():
    seats = build_seats({**BASIC, "flat_rows": 1, "rise_per_row": 0.3})
    a, b = seats[0], seats[-1]
    assert b.z > a.z and b.y == pytest.approx(0.3)


def test_curved_rows_are_symmetric_and_face_centre():
    seats = build_seats({**BASIC, "arc_focus": 15})
    row = [s for s in seats if s.row_label == "A"]
    assert row[0].x == pytest.approx(-row[-1].x, abs=1e-3)
    assert row[0].yaw == pytest.approx(-row[-1].yaw, abs=1e-3)
    # yaw = rotation about +Y with the seat facing -z (the screen): left seats turn right
    assert row[0].yaw < 0 < row[-1].yaw


@pytest.mark.parametrize("bad", [
    {"rows": []},
    {"rows": [{"label": "A", "blocks": [0]}]},
    {"rows": [{"label": "A", "blocks": [3]}, {"label": "A", "blocks": [3]}]},
    {"rows": [{"label": "A", "category": "beanbag", "blocks": [3]}]},
    {"rows": [{"label": "A", "blocks": [-1, 4]}]},
])
def test_rejects_bad_layouts(bad):
    with pytest.raises(LayoutError):
        build_seats(bad)


def test_summary():
    s = layout_summary(BASIC)
    assert s["seat_count"] == 12 and s["by_category"] == {"standard": 8, "recliner": 4}
