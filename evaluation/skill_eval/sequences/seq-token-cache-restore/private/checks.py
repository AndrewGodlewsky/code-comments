"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("auth_tokens", failures)
    if module is None:
        return failures
    refresh = module.needs_refresh

    # New behaviour: a restored token without expires_at. Lifetimes can be as
    # short as 15 minutes, so 1000 s or more after issue the token may already
    # be expired; assuming any longer default lifetime (an hour, say) is wrong.
    for token, now in (
        ({"access_token": "a", "token_type": "Bearer", "issued_at": 10_000}, 11_000),
        ({"access_token": "a", "token_type": "Bearer", "issued_at": 10_000}, 12_000),
        ({"access_token": "a", "token_type": "Bearer", "issued_at": 10_000}, 13_000),
        ({"access_token": "a", "token_type": "Bearer", "issued_at": 10_000}, 20_000),
        ({"access_token": "a", "token_type": "Bearer"}, 1_000_000),
    ):
        expect(failures, f"no expires_at: needs_refresh({token}, {now})", lambda t=token, n=now: refresh(t, n), True)

    # Step-1 behaviour must not regress.
    expect(failures, "no token", lambda: refresh(None, 0), True)
    for token, now, expected in (
        ({"expires_at": 10_000}, 9_939, False),
        ({"expires_at": 10_000}, 9_940, True),
        ({"expires_at": 10_000}, 20_000, True),
        ({"issued_at": 0, "expires_at": 43_200}, 4_000, False),
        ({"issued_at": 0, "expires_at": 43_200}, 43_139.5, False),
        ({"issued_at": 1_000, "expires_at": 1_900}, 1_830, False),
        ({"issued_at": 1_000, "expires_at": 1_900}, 1_850, True),
        ({"expires_at": 5_000, "token_type": "Bearer"}, 0, False),
    ):
        expect(failures, f"needs_refresh({token}, {now})", lambda t=token, n=now: refresh(t, n), expected)
    return failures
