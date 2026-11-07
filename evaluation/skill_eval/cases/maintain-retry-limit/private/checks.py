"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("policy", failures)
    if module is None:
        return failures
    resolve = module.resolve_retries
    for settings, override, expected in (
        ({}, None, 3), ({"retries": None}, None, 3), ({"retries": 0}, None, 0),
        ({"retries": 8}, None, 8), ({"retries": 2}, 0, 0), ({"retries": 0}, 6, 6),
        ({"retries": "unused"}, 8, 8),
    ):
        expect(failures, f"resolve_retries({settings}, {override})", lambda s=settings, o=override: resolve(s, o), expected)
    for invalid in (9, -1, True, False, "2", 1.5):
        expect_raises(failures, f"settings retries={invalid!r}", lambda v=invalid: resolve({"retries": v}), ValueError)
        expect_raises(failures, f"override={invalid!r}", lambda v=invalid: resolve({"retries": 2}, v), ValueError)
    return failures
