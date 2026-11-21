## Review of auth-04 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote the opening into a short summary of how sign-in works today and how the Google flow goes, then added a Terms section defining sub, attempt, pending link and identity in one line each
- Replaced the vague original flowchart and loose notes with a full flowchart covering both entry points, every callback outcome, the settings link, and the password-confirmation loop
- Turned the scattered notes into seven numbered steps, each with the same four parts (what starts it, what it does, where data lives, what happens on failure)
- Merged the duplicate remarks about errors, lockout, sessions and Google-only users into the steps and one failure table
- Moved state storage into one place: Redis attempt and pending link, both 10 minutes, deleted on use, plus the permanent user_identities table
- Kept failure handling to the simplest form: no locks, retries or takeover rules; relies on Redis delete-on-read and unique constraints
- Separated the build order from how the system runs, and put open questions last
- Dropped exact formats and library choices from the file

### Holes
- None.
