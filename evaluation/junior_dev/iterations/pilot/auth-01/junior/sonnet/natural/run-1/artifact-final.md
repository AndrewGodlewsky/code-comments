# Login with server-side sessions: design

## Context and requirements

- Server-rendered web app (HTML pages and form posts, no SPA or API clients).
- It runs as **two identical app instances behind a load balancer, with no sticky sessions**. Any request from a browser can reach either instance, so session state cannot live in one instance's memory. Which instance serves a request does not matter to this design: both run the same code against the same database.
- One Postgres database, which already has `users` (`id`, `email` stored lowercase and unique, `password_hash` bcrypt). Sign-up and password reset are out of scope.
- After this change every page except `/login` needs a signed-in user.

The requirements this design meets (numbered because later text refers to them):

1. `POST /login` takes email and password. Emails are matched in lowercase.
2. An unknown email and a wrong password get the identical response: HTTP 401 and the login page showing "Invalid email or password". Nothing may reveal whether an account exists.
3. Once an email has 5 failed attempts within any 10-minute period, refuse logins for that email for 15 minutes with HTTP 429, without checking the password. A successful login clears that email's failure count.
4. On success, always issue a brand-new random session ID, even if the browser already sent one, and destroy the session the incoming cookie pointed to. Then redirect to `/dashboard`.
5. The cookie carries only the opaque session ID, flagged HttpOnly, Secure and SameSite=Lax.
6. A session ends after 30 minutes with no requests (every request restarts that clock) or 12 hours after login, whichever comes first.
7. Every protected request checks the session on the server. If it is missing, unknown or expired, clear the cookie and redirect to `/login`.
8. `POST /logout` destroys the session on the server before replying, then clears the cookie and redirects to `/login`. It behaves the same when there is no session.

**Deliberately not decided here:** the language, web framework, database driver and connection-pool settings (including any statement timeout); how the load balancer picks an instance; how the login page template renders (it is the existing login page, given a status code and one message string; `GET /login` simply shows it, including to an already-signed-in user); and what `/dashboard` shows (it just loads the signed-in user's data by `user_id`). The design only fixes the behaviour below, which any stack can implement.

**Fixed choices that might look missing:**
- After login the redirect is always to `/dashboard`. There is no "return to the page you wanted" behaviour.
- Password hashing is unchanged. The dummy hash used for unknown emails is a bcrypt hash of an arbitrary constant string, made once at the same cost as the existing `password_hash` values.

## Decisions at a glance

| Choice | Decision |
|---|---|
| Where sessions live | Postgres, table `sessions`. No Redis. |
| Where failure counts live | Postgres, tables `login_failures` and `login_lockouts`. |
| Expiry check | One atomic `UPDATE ... RETURNING` on every protected request, using the database clock. |
| Expiry record | `created_at` and `last_seen_at` columns. No stored expiry timestamp. |
| Cleanup | Lazy delete on a failed lookup, plus a periodic sweep run by a timer in each instance. |
| Storage failure | Fail closed with an HTTP 503 page. Never fall through to "signed in". |
| Any unexpected error | Treated like a storage failure: roll back, 503, nothing granted. |

## Why Postgres and not Redis

- **Both instances already share Postgres.** Because requests can land on either instance, session state must be in a shared store. Postgres is already there, so there is no new component to deploy, monitor, secure or back up.
- **The load is small.** This is a small team-scheduling app serving server-rendered pages. One indexed primary-key write per page view is negligible for Postgres.
- **One transaction covers login.** Deleting the old session, inserting the new one and clearing failures commit or roll back together. Across Redis and Postgres that would need compensation logic.
- **Expiry needs one clock.** Both instances use Postgres `now()`, so clock skew between app hosts cannot let a session live longer on one instance.
- **The cost is a write per protected request**, because requirement 6 says every request restarts the idle clock. I accept this. If load grows, Redis is the natural upgrade behind the same three operations: create, touch-and-get, destroy. I would revisit it only when the data shows a problem.

## Data model

```sql
CREATE TABLE sessions (
  id_hash      bytea       PRIMARY KEY,           -- sha256 of the cookie value
  user_id      bigint      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at   timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX sessions_last_seen_idx ON sessions (last_seen_at);
CREATE INDEX sessions_created_idx   ON sessions (created_at);

CREATE TABLE login_failures (          -- one row per failed attempt
  email        text        NOT NULL,   -- normalized lowercase, may not exist in users
  attempted_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX login_failures_email_idx ON login_failures (email, attempted_at);

CREATE TABLE login_lockouts (
  email        text        PRIMARY KEY,
  locked_until timestamptz NOT NULL
);
```

- **Session ID.** It is 32 bytes from a CSPRNG, base64url-encoded. The cookie holds the raw value. The database stores only its SHA-256 hash, so a leaked database or backup cannot be replayed as live sessions.
- **How the hash is made.** Take the cookie value as a string, encode it as UTF-8 bytes, and compute SHA-256. The result is the raw 32 bytes (not a hex string), passed as the `bytea` parameter `$1`. Every place that hashes a cookie (login, protected request, logout) does exactly this.
- **No uniqueness check on new IDs.** 256 random bits make a collision practically impossible, so the app does not look for one first. If the insert ever hit a primary-key violation, that is a database error: roll back, 503, the user retries.
- **Failure counts are keyed by the submitted email.** The email does not have to exist in `users`. Unknown emails therefore lock exactly like real ones, and the 429 response reveals nothing about accounts.
- **`ON DELETE CASCADE`.** If a user row is ever deleted, their sessions vanish with it, so they are signed out on their next request (it takes the "no row" path below). No extra code is needed. If the user row is deleted while a login for that user is in progress, the session insert fails its foreign key; that is a database error (503), nothing is issued, and the retry gets the normal 401 for an unknown email.

## Rules that don't fit on the arrows

**Errors, in general**
- "Database error" means any exception from a database call: connection failure, query error, constraint violation, statement or lock timeout, or a failed COMMIT.
- Any other unexpected exception (for example bcrypt crashing, or the random generator failing when creating a session ID) is handled the same way: roll back any open transaction, log the details server-side, return the 503 response for that route (table under "When storage fails"). Database errors and unexpected errors always get the same page on a given route. Nothing is granted and no session is issued.
- Only `POST /login` sets an explicit `lock_timeout` (it is the only route that takes a lock). Other routes use plain single statements; if one is slow, the pool/driver statement timeout (not decided here) turns it into a database error.

**Cookie**
- Name `sid`, value is the opaque ID only.
- Flags: `HttpOnly; Secure; SameSite=Lax; Path=/`.
- It has no `Max-Age`, so it is a browser-session cookie. The server alone enforces expiry.
- Clearing sends the same name and attributes with `Max-Age=0`.
- The app always sets `Secure`, whatever scheme the request appears to use. Where TLS terminates (at the load balancer or the app) is a deployment matter this design does not decide, and it does not change the behaviour here. The deployment must serve the site over HTTPS, or browsers will not send the cookie back.
- A malformed `sid` value (not valid base64url, wrong length, junk) needs no special case. The app hashes the raw string without decoding it, finds no row, and takes the "unknown" path: cookie cleared, redirect to `/login`.
- If a request carries several `sid` cookies (for example one set on a different path), the app uses the first one it receives and ignores the rest. Only a cookie with `Path=/` is ever set by this app, so this should not happen in normal use. Clearing sends `Path=/` only.

**Login (`POST /login`)**
1. Normalize the email by trimming it and lowercasing it.
2. Open a transaction with `SET LOCAL lock_timeout = '5s'`, then take `pg_advisory_xact_lock(hashtext(email))`.
   - What it locks: not a table or row, but a number derived from the email. Only transactions that ask for the same number wait. Different emails do not block each other (a rare hash collision between two emails only makes them wait for each other, which is harmless).
   - When it is released: automatically when this transaction commits or rolls back, on every path below, including the 429 path (which rolls back). If the app process crashes or loses its connection mid-transaction, Postgres rolls the transaction back and releases the lock, so a crash cannot leave an email locked. It is held through the bcrypt check, so parallel guesses for one email run one at a time. Without it, a burst of concurrent requests could all pass the lockout check before any failure is recorded.
   - If the first request is slow (bcrypt, a database stall), a second request for the same email waits. After 5 seconds the wait fails, and it is handled as a database error (503, see "When storage fails"). No password is checked and no session is issued.
3. Read the lockout row, in the same transaction, before anything else: `SELECT locked_until, ceil(extract(epoch FROM locked_until - now())) AS retry_secs FROM login_lockouts WHERE email = $1`. If a row exists and `locked_until > now()`, roll back (releasing the advisory lock) and return 429 with `Retry-After: <retry_secs>` (a whole number of seconds written in decimal, such as `Retry-After: 840`) and the login page showing "Too many failed attempts. Please try again later." The password is not checked, and the attempt is not recorded as a failure. The message is the same for every email, whether or not it exists. The 429 page is the same login page as the 401 one; only the status, the `Retry-After` header and the message differ.
   - A row whose `locked_until` is already in the past is simply ignored: the email is not locked. It is overwritten by the upsert if the email locks again, and removed by the sweep otherwise.
4. Look up the user. If none exists, run bcrypt against the fixed dummy hash, so unknown and wrong-password cases take about the same time.
5. A bad email and a bad password both get HTTP 401 and the same login page with "Invalid email or password".
6. On failure, insert a `login_failures` row, then count with `SELECT count(*) FROM login_failures WHERE email = $1 AND attempted_at > now() - interval '10 minutes'`. The count is computed from timestamps, so it does not depend on the sweep having run. If the count is 5 or more, upsert `locked_until = now() + 15 minutes` (insert, or on conflict overwrite the existing row). All of this is committed before any response is sent. The attempt that records the fifth failure still gets the ordinary 401 with no sign of the lockout; the next attempt gets 429. This matches requirement 3: the limit applies once 5 failures exist.
7. The 15-minute lock is longer than the 10-minute window, so failures from before a lockout have aged out when it ends. The user starts fresh.
8. On success, in the same transaction:
   - delete the session the incoming cookie pointed to, if any;
   - delete this email's `login_failures` rows;
   - insert a new session with a new random ID;
   - commit, then redirect to `/dashboard` with the new cookie.
9. If the COMMIT itself fails, on the success or the failure path, it is a database error: 503 with the "Sign-in is temporarily unavailable" page, no `Set-Cookie`, and the old session untouched (nothing committed). The user can simply try again. On the failure path the attempt may or may not have been counted; that is acceptable.
10. The old session is destroyed even when the credentials are valid but the browser sent a stale or someone else's cookie.
11. A failed login (401) or a locked one (429) never touches the `sid` cookie or any existing session. No `Set-Cookie` is sent, and a session the browser already has stays valid.

**Error pages**
- Two kinds of page exist. Login responses (200 form, 401, 429, and the login 503) all use the existing login template with a status and one message. Every other 503 (protected routes, logout) uses a small generic error page that shows one message string; the app needs one such page, with the message set per route as in the table below. It is not the login template and has no sign-in form.

**Protected requests (every route except `/login`)**

How the check reaches every route: one shared piece of request-handling code (a middleware or filter) runs before every route handler. It exempts exactly one path, `/login` (both GET to show the form and POST to submit it). Everything else, including routes added later, is protected by default.
- Matching is on the request path only: the query string is ignored (`/login?next=x` is exempt). The match is exact, so `/login/` or `/Login` is not exempt; it is a protected path like any other and redirects to `/login` when there is no session.
- The handler runs only if the filter finds a valid session. `POST /logout` (matched by method and path) is the one protected route that does its own session handling (below): the filter passes it straight to the logout handler without requiring a valid session. Any other method on `/logout`, such as `GET /logout`, is not that route: it goes through the filter like any other protected path (no session means redirect to `/login`; a valid session reaches whatever the framework does for an unknown route or method, normally 404 or 405). It does not log anyone out.
- The 503 rule below applies to every protected route and method, including POSTs other than `/logout`.

If the request has no `sid` cookie, the app does not query the database. It goes straight to the "no session" path below. Otherwise it hashes the cookie value (that hash is `$1`) and runs one statement that checks the session and restarts the idle clock. It runs as its own auto-committed statement:

```sql
UPDATE sessions
   SET last_seen_at = now()
 WHERE id_hash = $1
   AND last_seen_at > now() - interval '30 minutes'   -- idle limit
   AND created_at   > now() - interval '12 hours'     -- absolute limit
RETURNING user_id;
```

- One row returned means the user is signed in. The app then loads whatever the page needs using that `user_id` (for `/dashboard`, the user's schedule data). If one of those later queries fails, the response is the same 503 page as any other database error; the session stays valid.
- No row means the cookie is unknown or expired. No cookie means missing. Either way, this "no session" path clears the cookie and redirects to `/login`.
- Because the check and the touch are one atomic statement, an expired session can never be revived by a concurrent request.
- `created_at` is never updated, so the 12-hour cap is not extendable.
- When a cookie was present but no row came back, the app also runs `DELETE FROM sessions WHERE id_hash = $1`. That cleans up an expired row immediately. Nothing depends on this delete for correctness, so it is best effort: if it fails, the error is logged and ignored, and the response is still the cookie clear and redirect to `/login` (not a 503).

**Logout (`POST /logout`)**
- If there is a cookie, run `DELETE FROM sessions WHERE id_hash = $1`. This is a no-op if the session is unknown. With no cookie, skip the database.
- Then clear the cookie and redirect to `/login`.
- The response is identical whether or not a session existed.
- The delete is committed before the reply is sent.
- If the delete fails (database error) or any other unexpected error happens, the response is the logout 503 below.

**Abandoned session cleanup**
- Each app instance runs its own timer inside the app process. It fires on startup and then every 10 minutes. No external scheduler is used.
- The sweep is idempotent, so two instances running it at once is harmless. No leader election is needed.
- It deletes `sessions` where `last_seen_at < now() - 30 min` or `created_at < now() - 12 h`.
- It deletes `login_failures` older than 10 minutes.
- It deletes `login_lockouts` where `locked_until < now()`.
- Sweep and live requests never fight over a row. The sweep deletes only rows that are already expired, and the protected-request `UPDATE` matches only rows that are not expired. A request that arrives for a row the sweep just deleted finds no row and takes the "unknown" path. Likewise the sweep only removes `login_failures` older than the 10-minute counting window and lockouts already in the past, which login ignores anyway.
- If a sweep fails, it logs the error and waits for the next tick. If an instance restarts, the timer simply starts again; the sweep holds no state. The other instance's sweep also covers the same tables.
- The sweep only keeps the tables small. Enforcement is the `WHERE` clause above, so a missed or failed sweep cannot make an expired session valid.

**When storage fails**

All of these fail closed. They apply to any database error or unexpected error as defined under "Errors, in general", with the same page for both.

| Situation | Response | Why |
|---|---|---|
| Protected request (any method), database or unexpected error | HTTP 503 generic error page: "Something went wrong on our side. Please try again." Cookie not cleared, no redirect to `/login`. | The session may still be valid. Clearing it would sign out users during an outage. |
| `POST /login`, database error, failed COMMIT, lock wait timeout or unexpected error | HTTP 503 and a login page saying "Sign-in is temporarily unavailable. Please try again." No session issued, no `Set-Cookie`. | If the lockout state can't be read, the attempt is refused rather than allowed unchecked. |
| `POST /logout`, delete fails or unexpected error | HTTP 503 generic error page: "We couldn't sign you out. Please try again." Cookie kept so a retry works. | Requirement 8 says the session is destroyed before replying. The app must not claim a logout it can't confirm. |

- 503 responses carry no information about accounts.
- Error details are logged server-side only.

**Out of scope or noted**
- CSRF protection beyond `SameSite=Lax` is not part of this change.
- Password hashing parameters are unchanged.
- An already-signed-in user opening `/login` just sees the login page. A successful login there replaces their session, as requirement 4 states.

## Sequence diagram

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant A as App instance (either one)
    participant D as Postgres

    Note over B,D: Login
    B->>A: POST /login (email, password, optional sid cookie)
    A->>A: normalize email (trim, lowercase)
    A->>D: BEGIN, lock_timeout 5s, advisory lock on email (held until COMMIT/ROLLBACK)
    A->>D: SELECT locked_until FROM login_lockouts WHERE email
    alt lock wait times out, database error or other unexpected error
        A->>D: ROLLBACK (if a transaction is open)
        A-->>B: 503 login page "Sign-in is temporarily unavailable" (no session, cookie untouched)
    else locked_until is in the future (lockout)
        A->>D: ROLLBACK (releases the advisory lock)
        A-->>B: 429 + Retry-After (whole seconds), login page "Too many failed attempts" (password never checked, cookie untouched)
    else not locked (no row, or locked_until already past)
        A->>D: SELECT id, password_hash FROM users WHERE email
        A->>A: bcrypt compare (dummy hash if no such user)
        alt password matches (success)
            A->>D: DELETE sessions WHERE id_hash = hash(incoming sid)
            A->>D: DELETE login_failures WHERE email
            A->>D: INSERT sessions (new random id, user_id)
            A->>D: COMMIT (if COMMIT fails: 503 as above, no cookie)
            A-->>B: 302 /dashboard + Set-Cookie sid=NEW (HttpOnly, Secure, SameSite=Lax)
        else unknown email or wrong password (bad credentials)
            A->>D: INSERT login_failures (email)
            A->>D: SELECT count FROM login_failures WHERE email AND attempted_at within last 10 min
            opt count is 5 or more
                A->>D: UPSERT login_lockouts locked_until = now() + 15 min (overwrites any old row)
            end
            A->>D: COMMIT (if COMMIT fails: 503 as above)
            A-->>B: 401 login page "Invalid email or password" (cookie untouched)
        end
    end

    Note over B,D: Protected page (a filter before every route except /login runs this)
    B->>A: GET /dashboard (sid cookie, may be absent)
    alt no sid cookie
        A-->>B: 302 /login + Set-Cookie sid= (Max-Age=0), no database call
    else cookie present
        A->>D: UPDATE sessions SET last_seen_at = now() WHERE id_hash AND idle under 30 min AND age under 12 h RETURNING user_id
        alt row returned (valid session)
            A->>D: load page data for user_id
            A-->>B: 200 page for that user
        else no row (unknown, expired or malformed cookie)
            A->>D: DELETE sessions WHERE id_hash (best-effort cleanup; failure is logged and ignored)
            A-->>B: 302 /login + Set-Cookie sid= (Max-Age=0)
        else database error (the UPDATE or page-data queries)
            A-->>B: 503 generic error page (cookie kept)
        end
    end

    Note over B,D: Logout
    B->>A: POST /logout (sid cookie, may be absent)
    A->>D: DELETE sessions WHERE id_hash (skipped if no cookie; no-op if no session)
    alt delete committed or nothing to delete
        A-->>B: 302 /login + Set-Cookie sid= (Max-Age=0)
    else database error or unexpected error
        A-->>B: 503 generic error page (cookie kept so retry works)
    end

    Note over A,D: Background, timer in each instance: on startup, then every 10 min
    A->>D: DELETE expired sessions, old login_failures, expired login_lockouts
```
