from app.services.viewing import SeatInfo, recommend, view_metrics

SCREEN = {"width": 14, "height": 6, "bottom": 1.4}


def test_centre_seat_beats_corner_seat():
    centre = view_metrics(0, 1.2, 14, SCREEN)
    corner = view_metrics(8, 0, 6, SCREEN)
    assert centre.score > corner.score
    assert corner.off_axis_deg > 40


def test_front_row_flags_neck_strain():
    front = view_metrics(0, 0, 3, SCREEN)
    assert front.vertical_deg > 20 and front.fov_deg > 100
    assert front.score < 50


def _row(label, n, block_break=None, taken=(), price=20000, cat="standard", score_fn=None):
    seats = []
    for i in range(1, n + 1):
        block = 1 if block_break and i > block_break else 0
        seats.append(SeatInfo(id=f"{label}{i}", row_label=label, number=i, block=block, grid_row=0, category=cat,
                              price_paise=price, score=score_fn(i) if score_fn else 80 - abs(i - n / 2) * 3,
                              available=i not in taken))
    return seats


def test_recommend_finds_contiguous_group_without_crossing_aisles():
    seats = _row("F", 10, block_break=5)
    opts = recommend(seats, 4)
    assert opts
    best = opts[0]
    nums = [int(x[1:]) for x in best["labels"]]
    assert best["together"]
    assert nums == list(range(nums[0], nums[0] + 4))
    assert all(n <= 5 for n in nums) or all(n > 5 for n in nums)


def test_recommend_respects_budget_and_availability():
    cheap = _row("A", 6, price=15000, score_fn=lambda i: 50)
    pricey = _row("B", 6, price=50000, cat="vip", score_fn=lambda i: 95)
    opts = recommend(cheap + pricey, 2, max_price_per_seat=20000)
    assert opts and all(o["row"] == "A" for o in opts)
    taken = _row("C", 3, taken=(2,))
    assert all(o["together"] is False for o in recommend(taken, 2)) or recommend(taken, 2) == []


def test_recommend_options_do_not_overlap():
    opts = recommend(_row("D", 12), 2, limit=5)
    ids = [i for o in opts for i in o["seat_ids"]]
    assert len(ids) == len(set(ids))
