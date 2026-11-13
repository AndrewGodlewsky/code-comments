## Goal

`orders-api` keeps three live third-party API keys (payments, email, geocoding) in `config/app.yaml`. That file is committed to the repo and copied into every container image. Move the keys into our managed secret store and change how the app reads them at runtime. The current setup is described in three files:

- `existing/app.yaml`: the repo's `config/app.yaml`.
- `existing/config_loader.py`: how the file is loaded and how the provider clients use the keys.
- `existing/deploy.md`: how we deploy and run locally.

## Fixed requirements

- Secrets go in the store under `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. The store encrypts them at rest with a per-environment KMS key and gives every write a new version id.
- The prod service identity `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else. Only the security on-call can write prod secrets. Engineers must not be able to read prod values.
- At startup the app must have all three keys before it reports ready. If the store can't be reached, retry 3 times, 2 seconds apart, then exit with a non-zero code.
- A running instance re-reads its secrets from the store every 5 minutes, so it picks up a new version without a restart. If a re-read fails, it keeps using the last good value and logs a warning.
- Key values exist only in process memory. They never go on disk, into environment variables or into logs. Logging version ids is fine.
- The current keys have been in git history for two years, so treat them as leaked. We are not rewriting history, so every key gets rotated at its provider. An old key may be revoked only after every running instance is confirmed to be using the new one.
- No customer request may fail because of a missing or revoked key at any point in the migration.
- Once the keys are out, CI must fail any change that puts an `api_key` back into `config/app.yaml`.
- Local development must keep working without anyone reading prod secrets.

## Not decided

Security has not decided yet whether keys must also be rotated on a regular schedule after this migration, or how often. Don't pick a cadence. Mark it as an open question.

## Format

Write a numbered, step-by-step plan in Markdown. Cover both the rollout and how the app reads keys at runtime. For each step, say what starts it, what moves where, where the state lives and what happens if it fails.
