-- Core app database (Postgres 15), owned by the core app team.
-- New services must not add tables here.

-- Transactional outbox: the core app inserts a row in the same
-- transaction as the business change it describes.
CREATE TABLE outbox (
  id           uuid PRIMARY KEY,         -- published downstream as event_id
  event_type   text NOT NULL,            -- e.g. 'invoice.paid'
  account_id   uuid NOT NULL,
  payload      jsonb NOT NULL,
  occurred_at  timestamptz NOT NULL,
  published_at timestamptz               -- set by outbox-relay
);

-- Customer webhook endpoints, written by the dashboard API.
CREATE TABLE webhook_subscriptions (
  id                uuid PRIMARY KEY,
  account_id        uuid NOT NULL,
  url               text NOT NULL,       -- always https
  event_types       text[] NOT NULL,     -- exact names, or '*' for all
  secret_ciphertext bytea NOT NULL,      -- plaintext via libs/secrets.decrypt()
  status            text NOT NULL DEFAULT 'active',  -- 'active' | 'disabled'
  disabled_reason   text,
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX webhook_subscriptions_account ON webhook_subscriptions (account_id);
