# Copyright 2026 Example Corp. Licensed under the Apache License, Version 2.0.
"""Validate usernames chosen at sign-up."""

import re

RESERVED = {"admin", "root", "support"}
# The LDAP directory stores uids as ASCII only, so reject anything else.
PATTERN = re.compile(r"[a-z0-9_]{3,20}")


def normalize_username(raw):
    # Logins are case-insensitive, so store the casefolded form; otherwise
    # "Alice" and "alice" could register as two different accounts.
    name = raw.strip().casefold()
    if not PATTERN.fullmatch(name):
        raise ValueError(f"invalid username: {raw!r}")
    if name in RESERVED:
        raise ValueError(f"reserved username: {raw!r}")
    return name
