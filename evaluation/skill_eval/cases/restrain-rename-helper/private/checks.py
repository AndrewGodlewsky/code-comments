"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("report", failures)
    if module is None:
        return failures
    if hasattr(module, "fmt"):
        failures.append("old name `fmt` still defined")
    if not hasattr(module, "format_dollars"):
        failures.append("`format_dollars` missing")
        return failures
    expect(failures, "format_dollars", lambda: module.format_dollars(12345), "$123.45")
    expect(failures, "line_item", lambda: module.line_item("Tea", 250), "Tea: $2.50")
    expect(failures, "total_line", lambda: module.total_line([("a", 100), ("b", 5)]), "Total: $1.05")
    return failures
