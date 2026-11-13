-- Tables that accounts/export.py fills each night, and billing's own invoices.
CREATE TABLE user_logins (
    user TEXT PRIMARY KEY,
    at TEXT NOT NULL,
    device TEXT NOT NULL
);

CREATE TABLE invoices (
    user TEXT NOT NULL,
    issued_at TEXT NOT NULL
);
