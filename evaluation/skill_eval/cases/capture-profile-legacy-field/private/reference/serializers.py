"""Serialize user profiles for the public API."""


def profile_json(user):
    display_name = (user.get("name") or "").strip() or user["username"]
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
    return [profile_json(user) for user in users if user.get("active", True)]
