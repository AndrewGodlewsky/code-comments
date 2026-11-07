"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("auth_tokens", failures)
    if module is None:
        return failures
    refresh = module.needs_refresh
    expect(failures, "no token", lambda: refresh(None, 0), True)
    for token, now, expected in (
        ({"expires_at": 10_000}, 9_939, False),
        ({"expires_at": 10_000}, 9_940, True),
        ({"expires_at": 10_000}, 10_000, True),
        ({"expires_at": 10_000}, 20_000, True),
        ({"issued_at": 0, "expires_at": 43_200}, 4_000, False),
        ({"issued_at": 0, "expires_at": 43_200}, 43_139.5, False),
        ({"issued_at": 1_000, "expires_at": 1_900}, 1_830, False),
        ({"issued_at": 1_000, "expires_at": 1_900}, 1_850, True),
        ({"expires_at": 5_000, "token_type": "Bearer"}, 0, False),
    ):
        expect(failures, f"needs_refresh({token}, {now})", lambda t=token, n=now: refresh(t, n), expected)
    return failures
