-- catalog database (Postgres 16). Primary host: catalog-primary
CREATE TABLE products (
  id           BIGINT PRIMARY KEY,
  sku          TEXT NOT NULL UNIQUE,
  title        TEXT NOT NULL,
  description  TEXT,
  price_cents  INTEGER NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived')),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rows are hard-deleted when a seller removes a product.
-- Search rule: only rows with status = 'active' may appear in search results.
-- About 40 million rows in total; roughly 300 writes/s at peak.

CREATE PUBLICATION catalog_search FOR TABLE products;
