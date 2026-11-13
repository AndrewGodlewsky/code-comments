# Login with server-side sessions: design

## Decisions

**D1. Sessions live in Postgres, in a new `sessions` table.** Both instances already share the database, so sessions work behind the load balancer with no sticky routing. We do not add Redis. At a small team's scale, one indexed primary-key lookup per request is cheap. Redis would add a new service to run, secure, back up and monitor. It would also give us a second store whose state can disagree with Postgres. Revisit if session lookups show up in load metrics.

```
sessions(
  id            text primary key,   -- SHA-256 hex of the cookie token
  user_id       bigint not null references users(id),
  created_at    timestamptz not null,
  last_seen_at  timestamptz not null,
  expires_at    timestamptz not null  -- created_at + 12 hours (absolute cap)
)
index on sessions(expires_at)
index on sessions(user_id)
```

- The session ID is 32 bytes from a CSPRNG, base64url-encoded. This is the cookie value (rule 5).
- Only the SHA-256 hash is stored, so a leaked database or backup cannot be replayed as live cookies.

**D2. Failure counts live in Postgres, in a `login_failures` table.** This is a separate table from sessions.

```
login_failures(
  email         text not null,      -- lowercase; may be an email with no account
  failed_at     timestamptz not null
)
index on (email, failed_at)
```

- The table is keyed by the submitted email, not by `users.id`. An unknown email therefore gets counted and locked out exactly like a real one (rule 2).
- Each failed attempt inserts one row.
- The lockout check counts rows for that email with `failed_at > now() - 10 minutes`.
- A lockout lasts until 15 minutes after the 5th failure in that window. Compute that moment as the `failed_at` of the 5th-newest row in the window, plus 15 minutes. While `now()` is before it, the email is locked.
- A row-per-failure design implements "5 failures within any 10-minute period" exactly. A fixed-window counter would not.
- A successful login deletes all rows for that email.
- Both instances see the same rows, so the limit holds regardless of which instance the load balancer picks.

**D3. Expiry is checked on every request, on the server, and recorded in the row.**
- A session is valid only if all of these hold:
  - `now() < expires_at`, which is the 12-hour cap.
  - `now() - last_seen_at < 30 minutes`, which is the idle timeout.
- Every valid request runs one statement that checks and renews in a single step. The check and the update cannot race between instances.

```sql
UPDATE sessions SET last_seen_at = now()
WHERE id = $hash AND expires_at > now() AND last_seen_at > now() - interval '30 minutes'
RETURNING user_id;
```

- Zero rows means the session is missing, unknown or expired. All three get the same handling (rule 7).
- Idle time restarts on each request. The absolute cap never moves. Whichever limit comes first ends the session.
- The cookie carries no expiry. It is a session cookie, and the server is the authority. Cookie lifetime is never trusted.
- All times come from the database clock (`now()`). This avoids clock skew between the two app instances.

**D4. Abandoned sessions are cleaned up two ways.**
- Correctness never depends on cleanup. Expired rows are already rejected by D3's query.
- Lazy: a request that finds an expired session also deletes that row.
- Sweep: a scheduled job runs every 15 minutes, on whichever instance gets there first. It runs `DELETE FROM sessions WHERE expires_at <= now() OR last_seen_at <= now() - interval '30 minutes'`. Running twice at once is harmless because the delete is idempotent. The same job deletes `login_failures` rows older than 25 minutes, which is past both the 10-minute counting window and the 15-minute lockout.

**D5. When storage fails, the app fails closed.**
- Any database error during login or a session check returns HTTP 503 with a generic "Something went wrong, please try again" page. The error is logged on the server.
- A storage error never counts as a failed login attempt.
- It never grants access.
- It never reveals whether an account exists.
- On a protected page, a storage error is not treated as "session invalid". The cookie is kept and the user is not redirected to `/login`. A brief database blip therefore does not sign everyone out. The user sees the 503 page and can retry.
- Logout when storage fails: clear the cookie and redirect to `/login`, but the server could not confirm destruction. The failure is logged. The session still dies at its normal expiry, and the sweep removes it. This is the one place where we choose to complete the user-visible action despite the error, because the user's intent is to leave.

## Other rules

- **Order of checks in `POST /login`.** Normalize the email to lowercase and look at the lockout state first. If locked, respond 429 without touching the password (rule 3). 429 says nothing about whether the account exists, because unknown emails get locked out too.
- **Identical 401.** Unknown email and wrong password both return 401 with the same body, "Invalid email or password". Neither branch has any other difference in headers or content.
- **Timing.** For an unknown email, run a bcrypt compare against a fixed dummy hash. Response time then does not reveal whether the account exists.
- **Each failure is recorded**, whether or not the account exists.
- **Session fixation (rule 4).** On success, always generate a new ID. If the request carried a cookie, delete that session row, valid or not. Insert the new row in the same transaction. Delete and insert are atomic, so there is no state with both sessions or neither.
- **Cookie.** `Set-Cookie: sid=<id>; HttpOnly; Secure; SameSite=Lax; Path=/`. There is no `Domain`, so the cookie is host-only. Clearing sets the same attributes with `Max-Age=0`.
- **CSRF.** SameSite=Lax blocks cross-site POSTs, including `POST /logout`. Cross-site form posts will not carry the cookie. No separate token is added.
- **Protected routes.** Middleware wraps every route except `GET /login` and `POST /login`. `POST /logout` is idempotent and behaves identically with or without a session.

## Sequence diagram

```mermaid
sequenceDiagram
    autonumber
    actor B as Browser
    participant A as App instance (either one)
    participant DB as Postgres

    rect rgb(235, 245, 255)
    Note over B,DB: Login
    B->>A: POST /login (email, password, optional old cookie)
    A->>A: lowercase the email
    A->>DB: count login_failures for email in last 10 min
    alt storage error
        DB--xA: error
        A-->>B: 503 "Something went wrong, please try again" (no failure recorded)
    else 5 or more failures, lockout still active
        DB-->>A: count and 5th-newest failed_at
        A-->>B: 429 locked out, password never checked
    else fewer than 5 failures, or lockout over
        DB-->>A: count
        A->>DB: SELECT id, password_hash FROM users WHERE email = lowercase email
        DB-->>A: user row or none
        A->>A: bcrypt compare (dummy hash if no user)
        alt unknown email or wrong password
            A->>DB: INSERT login_failures (email, now)
            A-->>B: 401 login page "Invalid email or password"
        else password matches
            A->>A: new random token, hash it
            A->>DB: BEGIN
            opt request carried an old cookie
                A->>DB: DELETE session for old cookie hash
            end
            A->>DB: INSERT session (hash, user_id, last_seen = now, expires = now + 12h)
            A->>DB: DELETE login_failures for email
            A->>DB: COMMIT
            A-->>B: 302 /dashboard, Set-Cookie sid (HttpOnly, Secure, SameSite=Lax)
        end
    end
    end

    rect rgb(240, 250, 240)
    Note over B,DB: Protected request
    B->>A: GET /dashboard (cookie sid)
    A->>DB: UPDATE sessions SET last_seen = now WHERE hash matches AND not past 12h AND idle under 30 min RETURNING user_id
    alt storage error
        DB--xA: error
        A-->>B: 503 generic error page (cookie kept)
    else no row (missing, unknown or expired)
        DB-->>A: 0 rows
        A->>DB: DELETE session by hash (best effort)
        A-->>B: 302 /login, clear cookie
    else row returned
        DB-->>A: user_id
        A-->>B: 200 page for that user
    end
    end

    rect rgb(255, 245, 235)
    Note over B,DB: Logout
    B->>A: POST /logout (cookie sid, or none)
    opt cookie present
        A->>DB: DELETE session by hash
        Note right of A: on storage error: log it, continue
    end
    A-->>B: 302 /login, clear cookie
    end
```

## Notes on the diagram

- **Bad credentials (step 4 onward).** The failure insert happens before the 401 is sent. The two causes, unknown email and wrong password, share one branch because they must be indistinguishable.
- **Lockout.** The 429 branch never reads `users` and never runs bcrypt. After the lockout time passes, the email is allowed to try again. Its old failures are no longer within the last 10 minutes, so the count is below 5.
- **Success.** Deleting the old session, creating the new one and clearing failures are in one transaction. Either the user is fully logged in or nothing changed.
- **Logout with no session.** The `DELETE` is skipped, and the response is the same 302 with the same cleared cookie.
- **Not covered here.** Sign-up and password reset are out of scope. Password reset should later delete all of a user's sessions, which the `user_id` index supports.
