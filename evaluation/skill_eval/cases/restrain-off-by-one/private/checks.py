"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("paging", failures)
    if module is None:
        return failures
    items = list(range(1, 46))
    expect(failures, "page 1", lambda: module.page_slice(items, 1), list(range(1, 21)))
    expect(failures, "page 2", lambda: module.page_slice(items, 2), list(range(21, 41)))
    expect(failures, "page 3", lambda: module.page_slice(items, 3), list(range(41, 46)))
    expect(failures, "page 4", lambda: module.page_slice(items, 4), [])
    expect(failures, "page 2 of size 10", lambda: module.page_slice(items, 2, 10), list(range(11, 21)))
    expect(failures, "empty page 1", lambda: module.page_slice([], 1), [])
    expect_raises(failures, "page 0", lambda: module.page_slice(items, 0), ValueError)
    expect(failures, "page_count", lambda: module.page_count(45), 3)
    expect(failures, "page_count exact", lambda: module.page_count(40), 2)
    expect(failures, "has_next 2", lambda: module.has_next(2, 45), True)
    expect(failures, "has_next 3", lambda: module.has_next(3, 45), False)
    return failures
