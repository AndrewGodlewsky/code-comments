"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


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
    stock = {"apple": 10, "pear": 2}
    expect(failures, "reserve returns units left", lambda: module.reserve(stock, "apple", 3), 7)
    expect(failures, "stock decremented", lambda: dict(stock), {"apple": 7, "pear": 2})
    expect(failures, "exactly all units returns int 0", lambda: module.reserve(stock, "pear", 2), 0)
    expect(failures, "stock at zero", lambda: dict(stock), {"apple": 7, "pear": 0})
    shortage(failures, module, "shortage", stock, "apple", 8, 7)
    shortage(failures, module, "sold out", stock, "pear", 1, 0)
    shortage(failures, module, "unknown sku", stock, "plum", 1, 0)
    if "plum" in stock:
        failures.append("unknown sku was added to stock")
    for bad in (0, -1, True, 1.5, "2"):
        before = dict(stock)
        expect_raises(failures, f"qty={bad!r}", lambda b=bad: module.reserve(stock, "apple", b), ValueError)
        if stock != before:
            failures.append(f"qty={bad!r}: stock changed")
    return failures
