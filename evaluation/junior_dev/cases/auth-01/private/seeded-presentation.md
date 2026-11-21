**auth / sessions**

The token (session key, the sid value) is 32 random bytes base64url and is the primary key of the sess table, which also has user_id, created_at and last_seen_at, and the cookie (named sid, HttpOnly, Secure, SameSite=Lax, Path=/, Max-Age=43200 which is 12 h) only ever holds that key and never any user data, and there's a cleanup thing every hour that removes sess rows idle more than 30 min or older than 12 h and also removes attempt rows older than 10 min and lock rows whose locked_until is past, and it can run on either app box (or both) since deleting twice doesn't hurt. Everything lives in Postgres, including the users table that already exists (id, email lowercase unique, password_hash bcrypt), and nothing is in process memory because there are two instances, so no Redis.

```mermaid
sequenceDiagram
    participant PG as PG sess
    participant C as Client
    participant X as Srv
    participant PG2 as attempts
    participant LK as lock tbl
    participant UT as users
    C->>X: POST /logout (cookie)
    X->>PG: DELETE by key
    X-->>C: 302 /login + clear
    Note right of PG: no-op if row missing, same reply. If DB down here then 503 and cookie NOT cleared so retry works
    C->>X: GET page
    X->>PG: lookup
    alt bad
        X->>PG: delete if exists
        X-->>C: 302 /login, Max-Age=0
    else ok
        X->>PG: touch
        X-->>C: 200 (their page)
    end
    Note over X,PG: bad = no cookie / no row / last_seen_at more than 30 min ago / created_at more than 12 h ago. touch = set last_seen_at to now. DB error = 503, page never served
    C->>X: POST /login
    X->>LK: check
    alt locked
        X-->>C: 429
    else
        X->>UT: find
        X->>X: bcrypt
        alt fail
            X->>PG2: count++
            opt 5+
                X->>LK: lock
            end
            X-->>C: 401
        else ok
            X->>PG2: delete
            X->>PG: delete old one (if cookie sent)
            X->>X: new token
            X->>PG: insert
            alt ok2
                X-->>C: 302 /dashboard + Set-Cookie
            else
                X-->>C: 503
            end
        end
    end
    Note left of C: 401 text is "Invalid email or password" for both unknown email and wrong pw
    Note right of UT: no user? still compare against a dummy bcrypt hash and still count++ so timing and lockout look identical
    Note over LK: locked = locked_until in the future. When locked the password is not checked, nothing gets counted and the lock is not extended
```

count++ means: insert a row with the email and failed_at = now into attempts (PG2 in the picture, login_failures really, one row per failure, not a counter column), then count how many of that email's rows have failed_at in the last 10 min, and there's no window start to reset, old rows just fall out of the count once they're more than 10 min old, and if the count is 5 or more that's the lock arrow, which writes locked_until = now + 15 min into login_locks (the lock tbl, keyed by the lowercased email), but that 5th one still gets the 401, not the 429. The email gets lowercased before any of this happens. When the session store insert fails after a good password (ok2 not ok) the user gets a 503 and no Set-Cookie and just isn't logged in (the old session would already be gone by then), and insert puts now into both created_at and last_seen_at. On a good login all of that email's attempt rows are deleted, which is the reset. The login token is fresh every time and never reuses whatever key the browser came in with.
