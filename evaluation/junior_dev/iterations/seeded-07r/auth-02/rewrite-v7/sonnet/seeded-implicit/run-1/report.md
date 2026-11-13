## Review of auth-02 (rewrite-v7, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote into the skill layout: summary, terms, rollout and runtime steps, failure table, open questions.
- Changed order: rotate keys at providers first and store only the new values, instead of storing the leaked values and rotating afterwards. This removes a dependency on the refresh mechanism during migration.
- Split the old step 5 so /healthz returns 503 until all three keys load (required by 'ready only after all three keys'), and secret_versions is used to confirm every pod runs the new version before revoking.
- Added an explicit verify step before revoking, and moved revoke to after it, per the brief.
- Added that clients must call secrets.get() per request, because they copied the key at construction.
- Added the rollback consequence: images from before the change contain revoked keys.
- Added the 3 retries 2 seconds apart then non-zero exit, the 5-minute refresh keep-last-good with a warning, access rules (read-only prod identity, security on-call writes, engineers cannot read prod), per-env KMS and version ids, the 30-day log retention reason, and dev reads sandbox keys under APP_ENV=dev.
- Defined terms: secret store, KMS key, service identity, version id, readiness probe, rolling deploy, rotate and revoke.
- Merged the 'don't log secret values' line into shared rules.
- Added an open question on whether providers allow two active keys, as an assumption the plan relies on. Kept the rotation schedule open question unchanged.

### Holes
- None.
