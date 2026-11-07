# Accept the upgraded backend's retry limit

We have finished the backend migration described in `docs/backend-upgrade.md`.
Update `resolve_retries` so it accepts any integer from zero through the new
maximum, and still rejects larger values. Keep the existing override, default
and type rules (including rejecting `bool`).
