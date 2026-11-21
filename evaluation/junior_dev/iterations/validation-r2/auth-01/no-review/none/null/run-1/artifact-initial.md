## Login, sessions and logout

**Where state lives.** Everything is in the existing Postgres database, which both app instances share. Nothing is held in process memory, so no new infrastructure (no Redis) is needed.

| Where | What it holds | Who writes it |
|---|---|---|
| `users` (existing) | id, email (lowercase, unique), password_hash (bcrypt) | sign-up (out of scope) |
| `sessions` (new) | id (32 random bytes, base64url, primary key), user_id, created_at, last_seen_at | inserted at login. Each valid request updates last_seen_at. Deleted at logout, when found expired, and by the cleanup job |
| `login_failures` (new) | one row per failed attempt: email (lowercase), failed_at. Indexed on (email, failed_at) | inserted by each failed login. A successful login deletes that email's rows. The cleanup job deletes rows older than 10 min |
| `login_locks` (new) | email (lowercase, primary key), locked_until | written when a failure brings the email's 10-minute count to 5. Deleted by the cleanup job once locked_until has passed |
| Browser cookie `sid` | the session ID only, no user data. HttpOnly, Secure, SameSite=Lax, Path=/, Max-Age=43200 (12 h) | set at login. Cleared (Max-Age=0) at logout or when the session is invalid |

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as App server (either instance)
    participant K as login_locks table
    participant F as login_failures table
    participant U as users table
    participant S as sessions table

    Note over B,S: 1. Login
    B->>A: POST /login with email, password (and an old sid cookie, if any)
    A->>A: Lowercase the email
    A->>K: Read the lock row for this email
    alt locked_until is in the future
        A-->>B: 429 Too many attempts (password not checked, attempt not recorded)
    else not locked
        A->>U: Find user by email
        A->>A: bcrypt-compare the password (against a dummy hash if no user)
        alt no such user, or password does not match
            A->>F: Insert a row (email, failed_at = now)
            A->>F: Count rows for this email with failed_at in the last 10 min
            opt count is 5 or more
                A->>K: Upsert locked_until = now + 15 min
            end
            A-->>B: 401 login page with "Invalid email or password"
        else password matches
            A->>F: Delete all rows for this email (failure count reset)
            opt request carried an old sid
                A->>S: Delete the old session row
            end
            A->>A: Generate a new random session ID
            A->>S: Insert id, user_id, created_at = now, last_seen_at = now
            alt insert fails
                A-->>B: 503 error page, no Set-Cookie (user stays logged out)
            else insert succeeds
                A-->>B: 302 to /dashboard, Set-Cookie sid = new ID
            end
        end
    end

    Note over B,S: 2. Request for any protected page
    B->>A: GET /any-page with sid cookie
    A->>S: Read the session row by sid (skipped if no cookie)
    alt no cookie, no row, idle over 30 min, or over 12 h since login
        A->>S: Delete the row if it exists
        A-->>B: 302 to /login, clear sid (Max-Age=0)
    else valid
        A->>S: Set last_seen_at = now (restarts the 30 min idle clock)
        A-->>B: 200 page for that user_id
    end

    Note over B,S: 3. Logout
    B->>A: POST /logout with sid cookie (if any)
    A->>S: Delete the session row by sid (no-op if already gone)
    A-->>B: 302 to /login, clear sid (Max-Age=0)

    Note over A,S: 4. Hourly cleanup job (any instance, repeated deletes are harmless)
    A->>S: Delete rows idle over 30 min or older than 12 h
    A->>F: Delete rows older than 10 min
    A->>K: Delete rows whose locked_until has passed
```

**Rules used in the diagram**
- **Counting failures (sliding window).** Every failed attempt adds one `login_failures` row. The server then counts that email's rows whose `failed_at` falls in the 10 minutes ending now. There is no stored window start and nothing resets the count on a timer: each failure simply stops counting once it is more than 10 minutes old. When the count is 5 or more, `login_locks.locked_until` is set to now + 15 min. That fifth attempt still gets the normal 401. Attempts made during the lock get 429 and add no row, so they cannot extend the lock. By the time the lock ends, the failures that caused it have all aged out of the 10-minute window.
- **Unknown emails.** The server still runs a bcrypt compare against a fixed dummy hash and records the failure. Response time and lockout therefore behave the same whether or not the account exists.
- **A session is valid** when a row exists for the cookie's ID, `now - last_seen_at` is at most 30 min, and `now - created_at` is at most 12 h.
- **Storage failures fail safe.** At login: 503, no cookie. On a protected page: 503, the page is not served. At logout: 503, and the cookie is left in place so the user can retry, because clearing it would hide a session that is still live.
