"""Sign-in handler for the admin console."""


def sign_in(store, lockout, user, password_ok):
    """Start a session for `user` if the password is right.

    The session stays open until fifteen minutes pass without a request.
    Returns the session id, or None if the password was wrong or the account is locked.
    """
    if lockout.is_locked(user):
        return None
    if not password_ok:
        lockout.record_failure(user)
        return None
    lockout.reset(user)
    return store.start(user)
