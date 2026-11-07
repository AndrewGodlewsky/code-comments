"""Serialize user profiles for the public API."""


def _display_name(user):
    """The person's name, or their username when the name is missing or blank."""
    return (user.get("name") or "").strip() or user["username"]


def _listed(user):
    """Whether the member directory lists this user; deactivated users are omitted."""
    return user.get("active", True)


def profile_json(user):
    display_name = _display_name(user)
    # Android app 4.x still reads the legacy "name" key and crashes without it,
    # so send it alongside display_name. Remove it once the minimum supported
    # Android version becomes 5.0 (forced upgrade on 2027-02-01).
    return {
        "id": user["id"],
        "display_name": display_name,
        "name": display_name,
        "avatar": user.get("avatar_url"),
    }


def public_profiles(users):
    """Profiles listed in the member directory; deactivated users are omitted."""
    return [profile_json(user) for user in users if _listed(user)]


def mention_json(user):
    """One @-mention autocomplete entry. New endpoint, so no legacy "name" key."""
    return {"id": user["id"], "display_name": _display_name(user), "handle": "@" + user["username"]}


def mention_suggestions(users, prefix):
    """Mention entries for directory-listed users whose username or display name starts with ``prefix`` (any case)."""
    prefix = prefix.casefold()
    return [
        mention_json(user) for user in users
        if _listed(user) and (user["username"].casefold().startswith(prefix)
                              or _display_name(user).casefold().startswith(prefix))
    ]
