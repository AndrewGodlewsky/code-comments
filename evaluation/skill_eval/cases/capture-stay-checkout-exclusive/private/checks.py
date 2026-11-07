"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""

from datetime import date


def check():
    failures = []
    module = load("stays", failures)
    if module is None:
        return failures
    if not hasattr(module, "availability_query"):
        return failures + ["availability_query is missing"]
    query = module.availability_query
    for first, last, checkin, checkout in (
        (date(2026, 3, 1), date(2026, 3, 1), "2026-03-01", "2026-03-02"),
        (date(2026, 2, 27), date(2026, 2, 28), "2026-02-27", "2026-03-01"),
        (date(2026, 12, 31), date(2026, 12, 31), "2026-12-31", "2027-01-01"),
        (date(2028, 2, 28), date(2028, 2, 29), "2028-02-28", "2028-03-01"),
        (date(2026, 4, 1), date(2026, 4, 30), "2026-04-01", "2026-05-01"),
    ):
        expect(failures, f"availability_query({first}, {last})", lambda f=first, l=last: query("H-17", f, l),
               {"hotel_id": "H-17", "checkin": checkin, "checkout": checkout})
    expect_raises(failures, "31 nights rejected", lambda: query("H-17", date(2026, 4, 1), date(2026, 5, 1)), ValueError)
    expect_raises(failures, "last before first rejected", lambda: query("H-17", date(2026, 4, 2), date(2026, 4, 1)), ValueError)
    expect(failures, "nights unchanged", lambda: module.nights(date(2026, 3, 1), date(2026, 3, 3)), 3)
    return failures
