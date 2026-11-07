"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""


def check():
    failures = []
    module = load("serializers", failures)
    if module is None:
        return failures
    full = {"id": 7, "name": "Ada Lovelace", "username": "ada", "avatar_url": "https://img/ada.png"}
    expect(failures, "named user", lambda: module.profile_json(full),
           {"id": 7, "display_name": "Ada Lovelace", "name": "Ada Lovelace", "avatar": "https://img/ada.png"})
    for label, user in (
        ("empty name", {"id": 8, "name": "", "username": "grace"}),
        ("whitespace name", {"id": 8, "name": "   ", "username": "grace"}),
        ("None name", {"id": 8, "name": None, "username": "grace"}),
        ("missing name", {"id": 8, "username": "grace"}),
    ):
        expect(failures, label, lambda u=user: module.profile_json(u),
               {"id": 8, "display_name": "grace", "name": "grace", "avatar": None})
    users = [full, {"id": 9, "name": "Off", "username": "off", "active": False}, {"id": 10, "name": " ", "username": "lin", "active": True}]
    expect(failures, "directory listing", lambda: module.public_profiles(users), [
        {"id": 7, "display_name": "Ada Lovelace", "name": "Ada Lovelace", "avatar": "https://img/ada.png"},
        {"id": 10, "display_name": "lin", "name": "lin", "avatar": None},
    ])
    return failures
