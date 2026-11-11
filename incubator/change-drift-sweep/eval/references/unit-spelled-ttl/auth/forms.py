"""Saving admin edit forms.

Edits are saved through the admin's session, so a form left idle for half an hour
can no longer be saved: the save goes to the sign-in page and the edits are lost.
"""


def save_form(store, session_id, form, saved):
    """Keep `form` in `saved` if the session is live, and return whether it was kept."""
    if not store.touch(session_id):
        return False
    saved.append(form)
    return True
