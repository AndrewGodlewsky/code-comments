# Copyright 2026 Example Corp. Licensed under the Apache License, Version 2.0.
"""Validate usernames chosen at sign-up."""

import re
import unicodedata

RESERVED = {"admin", "root", "support"}
PATTERN = re.compile(r"\w{3,20}")


def normalize_username(raw):
    # Logins are case-insensitive, so store the casefolded form; otherwise
    # "Alice" and "alice" could register as two different accounts.
    # NFKC as well: the identity provider treats uids that are equal after NFKC
    # normalization as one account, e.g. fullwidth or decomposed spellings.
    name = unicodedata.normalize("NFKC", raw.strip()).casefold()
    if not PATTERN.fullmatch(name):
        raise ValueError(f"invalid username: {raw!r}")
    if name in RESERVED:
        raise ValueError(f"reserved username: {raw!r}")
    return name
