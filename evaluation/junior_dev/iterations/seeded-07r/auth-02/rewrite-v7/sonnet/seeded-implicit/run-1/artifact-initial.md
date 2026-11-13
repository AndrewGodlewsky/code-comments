# Plan: API keys -> secret store

1. Access policies for `orders-api-prod`, security on-call, engineers.
2. Create secrets in the store: `orders-api/prod/{payments,email,geocoding}_api_key` (current values) and `orders-api/dev/*` (sandbox keys).
3. New `app/secrets.py` with `load()`, `refresh()`, `get(name)`. Retries on load. 5-min refresh.
4. Switch PaymentsClient / EmailClient / GeocodingClient to `secrets.get()`.
5. `/healthz`: add `secret_versions`.
6. Delete `api_key` entries from `config/app.yaml`. CI check for `api_key`.
7. `make run`: `APP_ENV=dev`.
8. Deploy + verify.
9. Rotate the three keys at the providers and revoke the old ones.
10. Update rollback notes in `deploy.md`.

Don't log secret values.

Open: rotation schedule (Security TBD).
