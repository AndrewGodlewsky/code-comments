"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""


ADA = {"id": 7, "name": "Ada Lovelace", "username": "ada", "avatar_url": "https://img/ada.png"}
BLANKS = (
    ("empty name", {"id": 8, "name": "", "username": "grace"}),
    ("whitespace name", {"id": 8, "name": "   ", "username": "grace"}),
    ("None name", {"id": 8, "name": None, "username": "grace"}),
    ("missing name", {"id": 8, "username": "grace"}),
)


def step1(module, failures):
    expect(failures, "profile of named user", lambda: module.profile_json(ADA),
           {"id": 7, "display_name": "Ada Lovelace", "name": "Ada Lovelace", "avatar": "https://img/ada.png"})
    for label, user in BLANKS:
        expect(failures, f"profile with {label}", lambda u=user: module.profile_json(u),
               {"id": 8, "display_name": "grace", "name": "grace", "avatar": None})
    users = [ADA, {"id": 9, "name": "Off", "username": "off", "active": False}, {"id": 10, "name": " ", "username": "lin", "active": True}]
    expect(failures, "directory listing", lambda: module.public_profiles(users), [
        {"id": 7, "display_name": "Ada Lovelace", "name": "Ada Lovelace", "avatar": "https://img/ada.png"},
        {"id": 10, "display_name": "lin", "name": "lin", "avatar": None},
    ])


def check():
    failures = []
    module = load("serializers", failures)
    if module is None:
        return failures
    step1(module, failures)
    if not (hasattr(module, "mention_json") and hasattr(module, "mention_suggestions")):
        return failures + ["mention_json or mention_suggestions is missing"]
    expect(failures, "mention of named user", lambda: module.mention_json(ADA),
           {"id": 7, "display_name": "Ada Lovelace", "handle": "@ada"})
    for label, user in BLANKS:
        expect(failures, f"mention with {label}", lambda u=user: module.mention_json(u),
               {"id": 8, "display_name": "grace", "handle": "@grace"})
    people = [
        ADA,
        {"id": 11, "name": "Alan Turing", "username": "turing"},
        {"id": 12, "name": "Adele Goldberg", "username": "adele", "active": False},
        {"id": 13, "name": "  ", "username": "alonzo", "active": True},
        {"id": 14, "name": "Grace Hopper", "username": "ghopper"},
    ]
    expect(failures, "prefix matches username or display name, any case, active only",
           lambda: module.mention_suggestions(people, "AL"), [
               {"id": 11, "display_name": "Alan Turing", "handle": "@turing"},
               {"id": 13, "display_name": "alonzo", "handle": "@alonzo"},
           ])
    expect(failures, "prefix on display name only", lambda: module.mention_suggestions(people, "gra"),
           [{"id": 14, "display_name": "Grace Hopper", "handle": "@ghopper"}])
    expect(failures, "deactivated user never suggested", lambda: module.mention_suggestions(people, "adel"), [])
    expect(failures, "no match", lambda: module.mention_suggestions(people, "zz"), [])
    return failures
