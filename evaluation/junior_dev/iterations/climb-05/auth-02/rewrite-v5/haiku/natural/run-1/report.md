## Review of auth-02 (rewrite-v5, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a "What this is" paragraph that first says how the system works today (keys read once at import from a committed file baked into the image, readiness means HTTP listening), then gives the main flow in eight short steps and why it is shaped that way.
- Added a Terms section defining every name and tool a newcomer needs (secret store, secret name, version id, KMS key, service identity, secret holder, refresh, readiness, liveness, provider overlap, revoke, image digest, soak window).
- Merged the separate Target state section into the intro and the scope section, and removed the duplicated scope and assumption bullets.
- Removed cross-references that sent the reader to other step codes (for example, B3, B5, A3, B1, B6) and replaced them with the names of the steps they refer to.
- Rewrote every step so it stands alone, with the same labels: starts, what it does, where the data lives, and what happens if it fails.
- Split the retry rule into the startup step and the failure cases, and stated the reading of "3 retries, 2 seconds apart" as one attempt plus 3 retries, about 6 seconds total.
- Kept the runtime design (Part A), local development (Part C), CI guard (Part D) and rollback (Part E) apart from the rollout (Part B), as the skill asks.
- Cut the detail of exact attempt times and the explicit list of pre-migration rollback targets, which reduced to one constraint: no pre-migration image after revocation.
- Merged the rollout checks for staging and the prod image into one step, and merged the secret-name rules into the terms and the access step.
- Removed the claim that the refresh changes behaviour for every key at once. Each key now swaps on its own, which is stated where the refresh is described.
- Kept all eight open questions, reworded so each one states the decision needed, and did not add any rotation cadence. The file stays within about 1.5 times the length of the original, with a Terms section and a few short added lines.

### Holes
- None.
