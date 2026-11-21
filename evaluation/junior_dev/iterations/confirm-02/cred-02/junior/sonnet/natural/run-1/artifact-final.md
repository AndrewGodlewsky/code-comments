# Two-factor sign-in with an authenticator app: state design

## Summary

Today a correct email and password calls `start_session`, which creates a `sessions` row and sets the `sid` cookie. This design adds optional TOTP two-factor sign-in (Google Authenticator, 1Password and similar apps). For a user with 2FA on, a correct password creates no session. It creates a short-lived "challenge" instead, and the session is created only after the user enters a valid authenticator code or an unused recovery code. The design is shaped so that an unfinished sign-in can never authenticate, and so that setting up or replacing an authenticator can never weaken the one that works today.

Two things are tracked: the account's long-lived 2FA lifecycle (stored per user) and one sign-in attempt (stored for at most 5 minutes). The only link between them is that a recovery-code sign-in can go straight to setting up a new authenticator.

## Terms

- **Time step**: TOTP (RFC 6238) cuts time into 30-second steps. The step number is Unix time divided by 30, rounded down. The app and the server each turn the shared secret and the step number into a 6-digit code. To check a typed code, the server computes the codes for the current step, the one before and the one after ("within ±1 step") and accepts a match.
- **`seal()` / `unseal()`**: existing helpers that encrypt and decrypt a secret with AES-GCM. The app key is held in the KMS (key service), not in the database.
- **Recovery code**: a random 10-character code (about 50 bits), shaped like `abcde-fghij`. It is never 6 digits, so the server can tell it from an authenticator code. To check one, the server lowercases the input, removes dashes and spaces, takes the SHA-256 and compares it with `code_hash` (stored the same way). So capitals and a missing dash do not matter. With 50 bits of randomness, plain SHA-256 is enough, and codes are shown only once.
- **Challenge**: the in-between state after a right password and before a second factor. It is a `login_challenges` row, deliberately not a `sessions` row.
- **QR code content**: a standard `otpauth://totp/...` link holding the base32 secret, the account email and the app name, with the usual defaults (6 digits, 30 seconds). The authenticator app reads it to learn the secret.
- **`enqueue_email`**: existing helper that puts an email on a queue. A background worker sends it and retries failures, so it never blocks or fails the request that queued it.

## Diagram

```mermaid
stateDiagram-v2
    direction LR

    state "Account 2FA lifecycle" as Lifecycle {
        [*] --> Off
        Off --> SetupPending : user starts setup with password, server makes secret and QR
        SetupPending --> SetupPending : wrong code, pending kept
        SetupPending --> Off : pending secret expires or is discarded
        SetupPending --> On : valid code, transaction C
        On --> ReplacePending : user starts replacement, password required
        ReplacePending --> ReplacePending : wrong code, old authenticator still works
        ReplacePending --> On : pending expires, old secret and codes unchanged
        ReplacePending --> On : valid code, transaction C swaps secret
        On --> Off : password and valid code, transaction D
        On --> LockedOut : phone lost and no unused recovery codes
    }

    state "Single sign-in attempt" as SignIn {
        [*] --> PasswordEntry
        PasswordEntry --> PasswordEntry : wrong password, 401, no state created
        PasswordEntry --> SignedIn : right password and 2FA off, start_session as today
        PasswordEntry --> Challenge : right password and 2FA on, no session yet
        Challenge --> SignedIn : valid authenticator code
        Challenge --> SignedInByRecovery : unused recovery code, code consumed, email queued
        Challenge --> Challenge : wrong entry, fewer than 5 so far
        Challenge --> PasswordEntry : 5th wrong entry or 5 minutes, challenge deleted
    }

    SignedInByRecovery --> ReplacePending : user starts new authenticator at once
    SignedInByRecovery --> On : user does nothing, 2FA stays on

    note right of LockedOut
        OPEN, not designed here.
        Product has not decided on support reset
        or identity checks.
    end note
```

## Where each piece of new state lives

All secrets and codes live in new tables. `sessions` and `start_session` are unchanged. Today `start_session` inserts a `sessions` row (SHA-256 of a new random token, 30-day expiry), sets the `sid` cookie (HttpOnly, Secure, SameSite=Lax, 30 days) and redirects to `/home`.

| State | Location | Notes |
|---|---|---|
| Active TOTP secret | `user_totp.secret_sealed` | Written with `seal()`, read with `unseal()`. 2FA is on only when `confirmed_at` is not null. |
| Pending secret | `user_totp.pending_secret_sealed`, `pending_expires_at` | Sealed. First setup and replacement use the same columns. During a replacement the old secret stays untouched in `secret_sealed`, so a replacement attempt never weakens or disables the current authenticator. Sign-in never reads the pending secret. Assumed lifetime 30 minutes (product to confirm). |
| Replay guard | `user_totp.last_step` (bigint) | The highest time step already accepted for the user. 0 before the first confirmation. |
| Recovery codes | `recovery_codes(user_id, code_hash, used_at)` | Hashes only. |
| Sign-in challenge | `login_challenges(token_hash, user_id, expires_at, failures)` | The raw token is in a short-lived `mfa` cookie (HttpOnly, Secure, SameSite=Lax, max-age 5 minutes). Only its hash is stored, like `sid`. Each password success makes its own challenge. If a user signs in twice, the older challenge stays valid until it expires, and each browser holds only its own cookie. |
| Wrong-entry log | one small table, one row per wrong second-factor entry | Drives the per-user limit (see "Limit across challenges"). |
| Session | `sessions`, unchanged | Created only by `start_session` after a second factor succeeds. |

Expiry is checked when a row is used: an expired pending secret counts as absent and an expired challenge is rejected. A periodic cleanup job deletes expired challenges and clears expired pending secrets, only to keep the tables small.

## What triggers each transition, and what happens on failure

**Pages.** Security settings is one page. When 2FA is off it offers "set up". When 2FA is on it offers "replace authenticator" and "turn off". Set-up and replace lead to the same "set up a new authenticator" page, which asks for the password and then shows the QR code.

**Turning 2FA on (`Off` to `SetupPending` to `On`)**
- Trigger: a signed-in user chooses "set up" and types the password. The server checks it with `bcrypt_check` before creating anything. A wrong password shows an error, creates no pending secret and counts toward the per-user limit. The password is asked so that a stolen session cannot turn on 2FA with the thief's authenticator and lock the owner out. This is my addition to the brief, for product to confirm.
- The server generates a secret and stores it as pending. If one already exists, it is overwritten and its expiry restarts, so the earlier QR code stops working. The QR code and secret are shown once. A user who closes the page starts setup again, which makes a new secret.
- Trigger: the user types a code. The server reads the pending secret from that user's own `user_totp` row. The code must be valid within ±1 step and its step must be greater than `last_step`.
- Success (transaction C), one database transaction. It is the same for first setup and replacement:
  - Moves the pending secret to the active secret and sets `confirmed_at` to now (on a replacement, the time of the latest confirmation). This applies only if the pending secret is still present and unexpired. So if two tabs confirm at once, the second finds none and sees "Setup already finished or expired, start again".
  - Deletes all old recovery codes and inserts 10 new hashed ones, so all previous codes stop working.
  - Sets `last_step` to the accepted step.
  - Deletes every other session of the user (`DELETE FROM sessions WHERE user_id=? AND token_hash<>current`). The current session stays. Challenges open in other browsers are not sessions and are untouched. If that person then enters a valid code, they get a new session as in any sign-in.
  - Returns the 10 plaintext codes in that one response and never stores them. If the user closes the page without saving them, they cannot be shown again. The only way to a new set is to replace the authenticator. There is no separate "regenerate codes" action.
- Failure: a wrong code or replayed step leaves the state as `SetupPending`, shows an error and counts toward the per-user limit. That limit is the only cap here, and no challenge is touched, because setup happens in a signed-in session. Sign-in still ignores the pending secret. If the pending secret expires, the state returns to `Off` with nothing else changed. If the transaction fails, nothing changes, including sessions and codes.

**Replacing the authenticator (`On` to `ReplacePending` to `On`)**
- Trigger: the user chooses "replace authenticator". This works in any signed-in session, including one that came from a recovery code, so a user with a lost phone can do it at once.
- The password is asked again, exactly as in first setup (same page, `bcrypt_check` before anything is created, wrong password counts toward the per-user limit). This applies even right after a recovery-code sign-in: one rule for every session, with no flag to remember where the session came from. It does not need the old authenticator, so it does not block the lost-phone case. Starting again while a pending secret exists overwrites it.
- The new secret's first code is checked against the same `last_step`, which still holds the step last accepted for the old secret. A code from that very same 30-second step is rejected, and the user waits for the next code.
- Success: transaction C. The old secret is replaced, a fresh set of 10 recovery codes replaces all earlier ones, and other sessions are signed out.
- Failure: wrong codes leave the old authenticator and old recovery codes working. An expired or abandoned replacement changes nothing. If the user types a code after the pending secret expired, the server treats the secret as absent and shows "Setup expired, start again". The old authenticator keeps working, and the user enters the password again for a new QR code.

**Signing in (single attempt)**
- Wrong password: the response is unchanged (401 "Wrong email or password") and nothing is created. The existing IP rate limit still applies. A right password is never counted or blocked by the per-user limit, which counts only wrong second-factor entries.
- Right password, 2FA off: `start_session` runs as today.
- Right password, 2FA on: no session and no `sid` cookie. The server inserts a `login_challenges` row (expiry now + 5 minutes, `failures` = 0), sets the `mfa` cookie and sends the user to the code page.
- Entering a code: the code page has one text field. Exactly 6 digits is an authenticator code, and anything else is a recovery code. Checks run in this order:
  1. Challenge: hash the `mfa` cookie and load the row. Its `user_id` says whose entry this is. If the cookie is missing (for example the code page was opened in another browser), or the challenge is expired or gone, the user returns to the password screen with the message below.
  2. Per-user limit: if already hit, the page shows "Too many attempts, try again later" without checking the code, and `failures` is not incremented. The only way forward is to wait. The challenge expires after 5 minutes, the password screen shows the timed-out message, and a new code page keeps showing the limit message until old entries age out of the hour.
  3. Code. An authenticator code must match within ±1 step and its step must be greater than `last_step`. The step is recorded with a guarded `UPDATE ... WHERE last_step < step`, so two simultaneous submissions cannot both pass. A recovery code is claimed with `UPDATE ... SET used_at=now() WHERE code_hash=? AND used_at IS NULL`, which must affect one row.
- Success deletes the challenge, clears the `mfa` cookie and calls `start_session`. The guarded update, the challenge delete and `start_session` are meant to be one transaction, so a failure before commit leaves the code unused (or the step unrecorded) and the challenge intact. Only the email comes after the commit. If `start_session` cannot join the transaction, see the open questions. For an authenticator code that costs little: the user waits for the next code.
- Recovery-code success also calls `enqueue_email(user_id, "recovery_code_used", {remaining})` after the commit. The email goes to `users.email` and says that a recovery code was used and how many remain (`remaining` is the count of the user's codes with `used_at` still null). It is the only notice the owner gets. Sign-in does not wait for the email and a send failure cannot fail it. If the enqueue call itself raises (queue down), the server logs the error and signs the user in anyway, and that notice is lost.
- After a recovery-code sign-in the session already exists. The server redirects to the "set up a new authenticator" page instead of `/home`, with a message that the phone may be lost. Nothing is forced and no flag is stored. The user can leave, and the session works normally.
- Any wrong entry (a bad code, an unknown recovery code, a replayed step) does two things in the same step: adds a row to the wrong-entry log and increments the challenge's `failures` atomically. On the fifth wrong entry, or once 5 minutes pass, the challenge row and cookie are deleted and the user returns to the password screen with: "Your sign-in timed out or had too many wrong codes. Enter your password again." A new challenge starts with a fresh count.
- Limit across challenges: restarting gives a fresh count, so the per-challenge limit alone does not stop an attacker who knows the password. One per-user limit therefore counts wrong second-factor entries across all challenges and all endpoints (sign-in code page, setup, replacement, turn-off). It is assumed to be 20 per hour, rolling, product to confirm. A correct entry does not reset it. When the limit is hit, those endpoints refuse further entries for that user, correct codes included, until old entries age out, and show "Too many attempts, try again later". It sits on top of the IP rate limit, which a spread-out attacker can avoid. Accepted trade-off: an attacker who knows the password can keep the owner out of the code step for up to an hour. The alternative is unlimited guessing.

**Turning 2FA off (`On` to `Off`)**
- Trigger: the user submits the password plus a valid authenticator code or an unused recovery code, in one form. The code field works as on the sign-in page.
- Checks run in this order: per-user limit, then password with `bcrypt_check`, then the code, checked as at sign-in (±1 step with the `last_step` guard, or the guarded recovery claim).
- Success (transaction D): in one transaction the server claims the code, deletes the `user_totp` row (active and pending secrets) and deletes all of the user's recovery codes. Other sessions stay signed in, since turning 2FA off already needs the password and a second factor.
- Failure: a wrong password, wrong code or replayed step leaves 2FA on, shows an error and counts toward the per-user limit. Nothing is deleted.

## Open questions

- Lost phone and no recovery codes (`LockedOut`): the state is deliberately a dead end. Product has not decided whether support may reset 2FA, or how they would check the person's identity. This plan does not design that path. Until it is decided, a user in that state cannot sign in. Someone must decide before launch, because every design here assumes the owner always holds a phone or a recovery code.
- Per-user limit: the 20 per hour figure and the rolling window are assumptions. It is not known whether the existing `rate_limit` helper can key on a user id. If it can, it could replace the wrong-entry table.
- Pending secret lifetime (30 minutes) and the password prompt on first setup and replacement are assumptions for product to confirm.
- Whether `start_session` can run inside the same transaction as the recovery-code claim or the `last_step` update is not known. If it cannot, a failure after the claim would use up a recovery code without signing the user in, and the user would enter the password again and use another code.
- The wording of the `recovery_code_used` email template is not specified here.