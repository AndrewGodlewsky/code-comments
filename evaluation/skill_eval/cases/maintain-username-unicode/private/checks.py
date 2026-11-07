"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("usernames", failures)
    if module is None:
        return failures
    normalize = module.normalize_username
    for raw, expected in (
        ("Alice", "alice"),
        ("  user_01 ", "user_01"),
        ("José", "josé"),
        ("José", "josé"),
        ("ＡＬＩＣＥ", "alice"),
        ("Straße", "strasse"),
        ("Ølaf_99", "ølaf_99"),
        ("Дмитрий", "дмитрий"),
        ("x" * 20, "x" * 20),
    ):
        expect(failures, f"normalize_username({raw!r})", lambda r=raw: normalize(r), expected)
    for raw in ("ab", "x" * 21, "bad name", "bad-name", "hi!there", "emoji\U0001F600x", "", "   "):
        expect_raises(failures, f"invalid {raw!r}", lambda r=raw: normalize(r), ValueError)
    for raw in ("Admin", "ROOT", "ａｄｍｉｎ"):
        expect_raises(failures, f"reserved {raw!r}", lambda r=raw: normalize(r), ValueError)
    return failures
