"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("policy", failures)
    if module is None:
        return failures
    if not hasattr(module, "retries_for_request"):
        return failures + ["policy.retries_for_request is missing"]

    # New behaviour: the X-Retries header is an override with resolve_retries' rules.
    per_request = module.retries_for_request
    for settings, headers, expected in (
        ({}, {}, 3),
        ({"retries": 2}, {}, 2),
        ({"retries": 2}, {"Accept": "application/json"}, 2),
        ({"retries": 2}, {"X-Retries": "5"}, 5),
        ({"retries": 2}, {"X-Retries": "0"}, 0),
        ({"retries": 0}, {"X-Retries": "6"}, 6),
        ({"retries": 2}, {"X-Retries": "8"}, 8),
    ):
        expect(failures, f"retries_for_request({settings}, {headers})",
               lambda s=settings, h=headers: per_request(s, h), expected)
    for value in ("9", "-1", "abc", "1.5", "true"):
        expect_raises(failures, f"X-Retries={value!r}",
                      lambda v=value: per_request({"retries": 2}, {"X-Retries": v}), ValueError)
    expect_raises(failures, "invalid settings without a header",
                  lambda: per_request({"retries": 9}, {}), ValueError)

    # Step-1 behaviour must not regress.
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
