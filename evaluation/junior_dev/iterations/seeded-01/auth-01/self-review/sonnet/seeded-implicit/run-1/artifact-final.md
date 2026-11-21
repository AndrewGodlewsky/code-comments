# Login with server-side sessions: design

## Summary

Every page except `/login` requires a signed-in user. After login, the browser holds one cookie, `sid`, containing a random opaque session ID. The session itself is a row in the existing Postgres database, so both app instances see the same data and no sticky sessions are needed. No new infrastructure is added.

## Design choices

**Where state lives: Postgres, not Redis.**
Process memory fails because the two instances don't share it. Redis isn't in the stack today, and adding it would mean a new service to run, monitor and secure. This is a small team app, so one extra indexed read or write per request is cheap. Postgres is already shared by both instances and already backed up. We don't add Redis.

**Tables.** Three new tables sit next to the existing `users` table.

| Table | Columns | Purpose |
|---|---|---|
| `sessions` | `id_hash` (primary key), `user_id`, `created_at`, `last_seen_at` | One row per signed-in browser. `id_hash` is the SHA-256 of the cookie value, so a database leak doesn't expose usable session IDs. |
| `login_failures` | `email`, `failed_at` (index on `email, failed_at`) | One row per failed login attempt. `email` is the submitted lowercase address, with no foreign key to `users`, so unknown emails are tracked exactly like real ones. |
| `login_locks` | `email` (primary key), `locked_until` | A row exists while that email is locked out. |

**Time source.** Every time comparison uses Postgres `now()`, never an instance's own clock, so the two instances can't disagree.

**How expiry is checked and recorded.**
No "expired" flag is stored. A session is valid only if both conditions hold:
- Idle limit: `now() - last_seen_at < 30 minutes`
- Absolute limit: `now() - created_at < 12 hours`

Each protected request runs one atomic statement that checks the session and renews it:

```sql
UPDATE sessions SET last_seen_at = now()
WHERE id_hash = $1
  AND last_seen_at > now() - interval '30 minutes'
  AND created_at   > now() - interval '12 hours'
RETURNING user_id;
```

Here `$1` is the SHA-256 of the cookie value. If a row comes back, the session is valid and its idle clock has restarted. If not, the session is missing, unknown or expired, so the app clears the cookie and redirects to `/login`. This costs one write per request, which is what "every request restarts the clock" requires. `created_at` never changes, so the 12-hour cap can't be extended.

**How abandoned sessions are removed.**
The query above already rejects expired rows, so cleanup is housekeeping, not a correctness requirement. A job runs every 10 minutes on each instance. Its deletes are idempotent, so overlapping runs are harmless. It deletes:
- sessions past either limit,
- `login_failures` rows older than 10 minutes,
- `login_locks` rows whose `locked_until` has passed.

**What the user sees when storage fails.**
The app fails closed: if the database can't be reached, it never treats anyone as signed in and never skips the lockout check. In every case the response is HTTP 503 with a plain page saying "Sign-in is temporarily unavailable. Please try again." Per route:
- **Login:** the failure is not counted as a bad attempt.
- **Protected page:** the cookie is not cleared, since the session may still be valid.
- **Logout:** the app cannot confirm the session was destroyed, so it doesn't claim success. It returns 503 and keeps the cookie so the user can retry.

## Rules that don't fit on the arrows

- **Email handling.** The submitted email is lowercased before every lookup, lock check and failure record.
- **Identical failures.** An unknown email and a wrong password both return HTTP 401 with the login page showing "Invalid email or password", and both record a failure the same way. For an unknown email the app still runs a bcrypt comparison against a dummy hash, so response time doesn't reveal whether the account exists.
- **Lockout.** After each failure, the app counts that email's `login_failures` rows from the last 10 minutes (a sliding window). If the count is 5 or more, it upserts `login_locks.locked_until = now() + 15 minutes`. While a lock is active, `POST /login` returns HTTP 429 without looking up the user or checking the password. Failed attempts during a lock are not recorded. The lock applies to any submitted email, so it reveals nothing about which accounts exist. Known limit: two simultaneous requests on different instances could let one extra attempt through before the lock is written. We accept that.
- **Success clears failures.** A successful login deletes that email's `login_failures` rows. (A locked email never reaches this point.)
- **Session fixation defense.** On success the app always generates a new session ID: 32 bytes from a cryptographically secure generator, base64url-encoded. If the request carried a `sid` cookie, the app deletes that old session in the same transaction that creates the new one. It then responds `303 See Other` to `/dashboard`.
- **Cookie.** `sid` holds only the opaque ID, with flags `HttpOnly; Secure; SameSite=Lax; Path=/`. No user data goes in it. It has no `Max-Age`, so it is a browser-session cookie, and the server enforces all expiry. To clear it, the app sends `sid` with an empty value and `Max-Age=0`.
- **Logout.** The app deletes the session row (a no-op if none exists), then always clears the cookie and redirects to `/login`. The result is the same whether or not a session existed.

## Sequence diagram

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as App (either instance)
    participant DB as Postgres

    Note over B,DB: Login
    B->>A: POST /login (email, password, optional old sid cookie)
    A->>A: lowercase the email
    A->>DB: is there a login_locks row for this email with locked_until in the future?
    alt locked
        A-->>B: 429 (password not checked)
    else not locked
        A->>DB: SELECT user by email
        A->>A: bcrypt compare (dummy hash if no such user)
        alt unknown email or wrong password
            A->>DB: INSERT login_failures; count failures in last 10 min
            opt count is 5 or more
                A->>DB: upsert login_locks, locked_until = now() + 15 min
            end
            A-->>B: 401, login page "Invalid email or password"
        else password correct
            A->>DB: transaction: DELETE old session (if cookie sent), INSERT new session, DELETE this email's login_failures
            A-->>B: 303 to /dashboard, Set-Cookie sid=new ID
        end
    end

    Note over B,DB: Protected page
    B->>A: GET /dashboard (sid cookie)
    A->>DB: UPDATE sessions SET last_seen_at = now() WHERE id_hash matches AND within 30 min idle AND within 12 h of creation
    alt row updated (valid)
        A-->>B: 200, page
    else no row (missing, unknown or expired)
        A-->>B: 302 to /login, clear sid cookie
    end

    Note over B,DB: Logout
    B->>A: POST /logout (sid cookie, may be absent)
    A->>DB: DELETE session by id_hash (no-op if none)
    A-->>B: 303 to /login, clear sid cookie

    Note over A,DB: If any DB call above fails: 503 "Sign-in is temporarily unavailable" (fail closed, see Design choices)
```
