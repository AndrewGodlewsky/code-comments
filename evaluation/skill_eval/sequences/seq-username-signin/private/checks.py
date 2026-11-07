"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("usernames", failures)
    if module is None:
        return failures
    if not hasattr(module, "find_account"):
        return failures + ["usernames.find_account is missing"]

    # New behaviour: sign-in lookup against stored (NFKC + casefolded) names.
    alice, jose, admin, strasse = {"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}
    users = {"alice": alice, "josé": jose, "admin": admin, "strasse": strasse}
    find = module.find_account
    for typed, expected in (
        ("alice", alice),
        ("Alice", alice),
        ("  alice ", alice),
        ("ADMIN", admin),
        ("Straße", strasse),
        ("José", jose),
        # The edge cases below depend on NFKC, not just casefold.
        ("ＡＬＩＣＥ", alice),
        ("José", jose),
        ("ＪＯＳÉ", jose),
        ("ａｄｍｉｎ", admin),
    ):
        expect(failures, f"find_account({typed!r})", lambda t=typed: find(users, t), expected)
    for typed in ("bob", "bad name!", "", "   ", "x" * 30, "emoji\U0001F600x"):
        expect(failures, f"find_account({typed!r}) is None", lambda t=typed: find(users, t), None)

    # Step-1 behaviour must not regress.
    normalize = module.normalize_username
    for raw, expected in (
        ("Alice", "alice"), ("  user_01 ", "user_01"), ("José", "josé"), ("José", "josé"),
        ("ＡＬＩＣＥ", "alice"), ("Straße", "strasse"), ("Дмитрий", "дмитрий"),
    ):
        expect(failures, f"normalize_username({raw!r})", lambda r=raw: normalize(r), expected)
    for raw in ("ab", "x" * 21, "bad name", "bad-name", "", "Admin", "ａｄｍｉｎ"):
        expect_raises(failures, f"sign-up rejects {raw!r}", lambda r=raw: normalize(r), ValueError)
    return failures
