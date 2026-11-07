"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""


def shortage(failures, module, label, stock, sku, qty, available):
    before = dict(stock)
    try:
        result = module.reserve(stock, sku, qty)
    except module.InsufficientStock as error:
        got = (getattr(error, "sku", None), getattr(error, "requested", None), getattr(error, "available", None))
        if got != (sku, qty, available):
            failures.append(f"{label}: InsufficientStock carries {got!r}, expected {(sku, qty, available)!r}")
    except Exception as error:
        failures.append(f"{label}: expected InsufficientStock, raised {type(error).__name__}: {error}")
    else:
        failures.append(f"{label}: expected InsufficientStock, got {result!r}")
    if stock != before:
        failures.append(f"{label}: stock changed to {stock!r}")


def check():
    failures = []
    module = load("inventory", failures)
    if module is None:
        return failures
    if not hasattr(module, "release"):
        return failures + ["inventory.release is missing"]

    # New behaviour: release.
    stock = {"apple": 7, "pear": 0}
    expect(failures, "release returns units in stock", lambda: module.release(stock, "apple", 3), 10)
    expect(failures, "release onto zero", lambda: module.release(stock, "pear", 2), 2)
    expect(failures, "release of a new sku", lambda: module.release(stock, "plum", 4), 4)
    expect(failures, "stock after releases", lambda: dict(stock), {"apple": 10, "pear": 2, "plum": 4})
    for bad in (0, -1, True, 1.5, "2"):
        before = dict(stock)
        expect_raises(failures, f"release qty={bad!r}", lambda b=bad: module.release(stock, "apple", b), ValueError)
        if stock != before:
            failures.append(f"release qty={bad!r}: stock changed to {stock!r}")
    expect_raises(failures, "release qty=0 on a new sku", lambda: module.release(stock, "kiwi", 0), ValueError)
    if "kiwi" in stock:
        failures.append("rejected release added kiwi to stock")

    # Step-1 behaviour must not regress.
    stock = {"apple": 10, "pear": 2}
    expect(failures, "reserve returns units left", lambda: module.reserve(stock, "apple", 3), 7)
    expect(failures, "reserve exactly all units", lambda: module.reserve(stock, "pear", 2), 0)
    shortage(failures, module, "shortage", stock, "apple", 8, 7)
    shortage(failures, module, "sold out", stock, "pear", 1, 0)
    shortage(failures, module, "unknown sku", stock, "plum", 1, 0)
    for bad in (0, -1, True, 1.5, "2"):
        expect_raises(failures, f"reserve qty={bad!r}", lambda b=bad: module.reserve(stock, "apple", b), ValueError)
    expect(failures, "reserve after release round-trip", lambda: (module.release(stock, "pear", 1), module.reserve(stock, "pear", 1)), (1, 0))
    return failures
