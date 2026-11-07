"""Serialize user profiles for the public API."""


def profile_json(user):
    return {
        "id": user["id"],
        "name": user["name"],
        "avatar": user.get("avatar_url"),
    }


def public_profiles(users):
    """Profiles listed in the member directory; deactivated users are omitted."""
    return [profile_json(user) for user in users if user.get("active", True)]
