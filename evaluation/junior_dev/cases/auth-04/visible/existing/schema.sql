-- Current auth tables (PostgreSQL 15). Emails are stored lowercased.

CREATE TABLE users (
  id                BIGSERIAL PRIMARY KEY,
  email             TEXT NOT NULL UNIQUE,   -- lowercased on every write
  password_hash     TEXT NOT NULL,          -- bcrypt, cost 12
  email_verified_at TIMESTAMPTZ,            -- NULL until the verify link is used
  failed_logins     INT NOT NULL DEFAULT 0, -- see auth_flow.md, lockout
  locked_until      TIMESTAMPTZ,            -- NULL when not locked
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  id         TEXT PRIMARY KEY,              -- 32 random bytes, base64url; the sid cookie value
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL           -- 14 days ahead, slid forward on each request
);

CREATE TABLE password_reset_tokens (
  token_hash TEXT PRIMARY KEY,              -- sha256 of the emailed token
  user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL           -- 1 hour after issue
);
