class UserNotFound(LookupError):
    """No user is registered under the requested key."""


class UserStore:
    def __init__(self):
        self._ids_by_email = {}
        self._emails_by_id = {}

    def add(self, user_id, email):
        key = email.strip().lower()
        # Refuse duplicates instead of overwriting: silently re-pointing an email
        # at a new id would hand the old account to whoever signed up last.
        if key in self._ids_by_email:
            raise ValueError(f"email already registered: {email}")
        self._ids_by_email[key] = user_id
        self._emails_by_id[user_id] = key

    def find_by_email(self, email):
        """Look up a user id by email address.

        Matching is case-sensitive. Returns None when no user has that email.
        """
        key = email.strip().lower()
        if key not in self._ids_by_email:
            raise UserNotFound(email)
        return self._ids_by_email[key]

    def email_of(self, user_id):
        """Return the email address registered for ``user_id``."""
        return self._emails_by_id[user_id]
