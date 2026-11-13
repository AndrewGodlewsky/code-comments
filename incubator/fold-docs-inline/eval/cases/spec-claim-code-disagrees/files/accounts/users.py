"""The account directory."""

from accounts.names import normalise_name

DEFAULT_ROLE = "member"


class NameTaken(Exception):
    """Another account already uses this name."""


class Directory:
    def __init__(self):
        self._accounts = {}

    def register(self, name):
        key = normalise_name(name)
        if key in self._accounts:
            raise NameTaken(name)
        self._accounts[key] = {"name": key, "role": DEFAULT_ROLE}
        return self._accounts[key]

    def find_user(self, name):
        """Return the account with this name, or None."""
        return self._accounts.get(normalise_name(name))

    def grant_role(self, actor, name, role):
        account = self._accounts[normalise_name(name)]
        if role == "editor" and actor["role"] != "admin":
            raise PermissionError("only an admin can grant the editor role")
        account["role"] = role
