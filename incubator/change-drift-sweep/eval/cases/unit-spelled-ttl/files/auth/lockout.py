"""Account lockout after repeated failed sign-ins."""

from auth.settings import MAX_FAILED_LOGINS


class Lockout:
    def __init__(self):
        self.failures = {}

    def record_failure(self, user):
        self.failures[user] = self.failures.get(user, 0) + 1

    def is_locked(self, user):
        # Lock the account after 15 failed sign-ins in a row.
        return self.failures.get(user, 0) >= MAX_FAILED_LOGINS

    def reset(self, user):
        self.failures.pop(user, None)
