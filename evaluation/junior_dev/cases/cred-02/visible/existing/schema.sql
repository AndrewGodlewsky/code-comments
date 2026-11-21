-- existing/schema.sql -- current auth tables (PostgreSQL 15)
CREATE TABLE users (
  id            bigserial PRIMARY KEY,
  email         text NOT NULL UNIQUE,
  password_hash text NOT NULL,          -- bcrypt, cost 12
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  token_hash  bytea PRIMARY KEY,        -- sha256 of the cookie value; the raw token is never stored
  user_id     bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL
);
CREATE INDEX sessions_user_idx ON sessions (user_id);

-- Helpers that already exist:
--   app.security.seal(plaintext) -> blob, unseal(blob) -> plaintext
--       AES-GCM with the app key held in the KMS. Use for any secret stored at rest.
--   app.security.bcrypt_check(plain, hash), new_token(n_bytes), rate_limit(...)
--   app.mailer.enqueue_email(user_id, template, data)
--       Puts the email on a queue. A failed send is retried in the background and
--       never blocks or fails the request that queued it.
