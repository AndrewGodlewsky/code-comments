# Copyright 2026 Example Corp. Licensed under the Apache License, Version 2.0.
"""Validate usernames chosen at sign-up and find accounts at sign-in."""

import re
import unicodedata

RESERVED = {"admin", "root", "support"}
PATTERN = re.compile(r"\w{3,20}")


def canonical_username(raw):
    """Return the form usernames are stored and compared in.

    Sign-up and sign-in must both use this, or a stored name and the name a
    person types can disagree about who the account is.
    """
    # Logins are case-insensitive, so store the casefolded form; otherwise
    # "Alice" and "alice" could register as two different accounts.
    # NFKC as well: the identity provider treats uids that are equal after NFKC
    # normalization as one account, e.g. fullwidth or decomposed spellings.
    return unicodedata.normalize("NFKC", raw.strip()).casefold()


def normalize_username(raw):
    name = canonical_username(raw)
    if not PATTERN.fullmatch(name):
        raise ValueError(f"invalid username: {raw!r}")
    if name in RESERVED:
        raise ValueError(f"reserved username: {raw!r}")
    return name


def find_account(users, typed):
    """Return the account record in ``users`` for the name typed at sign-in, or None.

    Applies no sign-up rules: staff accounts use reserved names, and a name
    that sign-up would reject simply has no record.
    """
    return users.get(canonical_username(typed))
