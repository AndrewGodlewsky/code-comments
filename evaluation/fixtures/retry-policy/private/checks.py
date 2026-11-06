"""Independent behavioral checks for trusted fixture sources, not a sandbox."""


def check(source: str, step: int) -> list[str]:
    if step not in (0, 1, 2, 3):
        raise ValueError("step must be 0, 1, 2 or 3")
    namespace = {}
    failures = []
    try:
        exec(compile(source, "trusted_fixture.py", "exec"), namespace)
    except Exception as error:
        return [f"load: {type(error).__name__}: {error}"]

    def expect(name, arguments, expected=None, invalid=False):
        try:
            actual = namespace[name](**arguments)
        except ValueError:
            if not invalid:
                failures.append(f"{name}{arguments}: unexpected ValueError")
        except Exception as error:
            failures.append(f"{name}{arguments}: {type(error).__name__}")
        else:
            if invalid or type(actual) is not type(expected) or actual != expected:
                failures.append(f"{name}{arguments}: expected {'ValueError' if invalid else repr(expected)}, got {actual!r}")

    maximum = 5 if step < 2 else 8
    for settings, expected in (({}, 3), ({"retries": None}, 3), ({"retries": 0}, 0), ({"retries": 2}, 2), ({"retries": maximum}, maximum)):
        expect("resolve_retries", {"settings": settings}, expected)
    for invalid in (True, False, -1, maximum + 1, "2", 1.5):
        expect("resolve_retries", {"settings": {"retries": invalid}}, invalid=True)
    if step >= 1:
        for settings, override, expected in (({}, None, 3), ({"retries": 0}, None, 0), ({"retries": 2}, 0, 0), ({"retries": 0}, 2, 2), ({"retries": "unused"}, maximum, maximum)):
            expect("resolve_retries", {"settings": settings, "override": override}, expected)
        for invalid in (True, False, -1, maximum + 1, "2", 1.5):
            expect("resolve_retries", {"settings": {"retries": 2}, "override": invalid}, invalid=True)
    if step == 3:
        for settings, override, expected in (({}, None, [1, 2, 4]), ({"retries": 0}, None, []), ({"retries": 8}, 0, []), ({"retries": 0}, 1, [1]), ({"retries": 5}, None, [1, 2, 4, 4, 4]), ({}, 8, [1, 2, 4, 4, 4, 4, 4, 4])):
            expect("retry_delays", {"settings": settings, "override": override}, expected)
        for invalid in (True, -1, 9, "2", 1.5):
            expect("retry_delays", {"settings": {"retries": invalid}}, invalid=True)
            expect("retry_delays", {"settings": {}, "override": invalid}, invalid=True)
    return failures
