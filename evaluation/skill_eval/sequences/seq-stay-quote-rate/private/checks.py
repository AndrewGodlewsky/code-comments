"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""

from datetime import date


def step1(module, failures):
    if not hasattr(module, "availability_query"):
        failures.append("availability_query is missing")
        return
    query = module.availability_query
    for first, last, checkin, checkout in (
        (date(2026, 3, 1), date(2026, 3, 1), "2026-03-01", "2026-03-02"),
        (date(2026, 12, 31), date(2026, 12, 31), "2026-12-31", "2027-01-01"),
        (date(2028, 2, 28), date(2028, 2, 29), "2028-02-28", "2028-03-01"),
        (date(2026, 4, 1), date(2026, 4, 30), "2026-04-01", "2026-05-01"),
    ):
        expect(failures, f"availability_query({first}, {last})", lambda f=first, l=last: query("H-17", f, l),
               {"hotel_id": "H-17", "checkin": checkin, "checkout": checkout})
    expect_raises(failures, "31 nights rejected", lambda: query("H-17", date(2026, 4, 1), date(2026, 5, 1)), ValueError)
    expect_raises(failures, "last before first rejected", lambda: query("H-17", date(2026, 4, 2), date(2026, 4, 1)), ValueError)
    expect(failures, "nights unchanged", lambda: module.nights(date(2026, 3, 1), date(2026, 3, 3)), 3)


def quote(checkin, checkout, total):
    return {"hotel_id": "H-17", "checkin": checkin, "checkout": checkout, "total_cents": total}


def check():
    failures = []
    module = load("stays", failures)
    if module is None:
        return failures
    step1(module, failures)
    if not hasattr(module, "nightly_rate"):
        return failures + ["nightly_rate is missing"]
    rate = module.nightly_rate
    for checkin, checkout, total, expected in (
        ("2026-05-04", "2026-05-09", 61000, 12200),   # five nights
        ("2026-03-01", "2026-03-02", 12000, 12000),   # a single night
        ("2026-12-31", "2027-01-01", 9999, 9999),
        ("2028-02-28", "2028-03-01", 30001, 15000),   # leap day, rounded down
        ("2026-04-01", "2026-05-01", 90000, 3000),
    ):
        expect(failures, f"nightly_rate {checkin}..{checkout} total {total}", lambda q=quote(checkin, checkout, total): rate(q), expected)
    expect_raises(failures, "checkout equal to checkin rejected", lambda: rate(quote("2026-03-01", "2026-03-01", 12000)), ValueError)
    expect_raises(failures, "checkout before checkin rejected", lambda: rate(quote("2026-03-02", "2026-03-01", 12000)), ValueError)
    # A quote for the stay we asked about prices the same nights the guest books.
    body = module.availability_query("H-17", date(2026, 6, 10), date(2026, 6, 13))
    expect(failures, "rate of a quote built from availability_query", lambda: rate({**body, "total_cents": 48000}), 12000)
    return failures
