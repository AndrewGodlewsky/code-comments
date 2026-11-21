# Login with Server-Side Sessions: Design

## Decisions

**1. Storage: add Redis (one instance, shared by both app instances).**
- Both app instances must see the same sessions and failure counts, and there are no sticky sessions, so process memory is out.
- Redis is chosen over Postgres for three reasons. Every protected request reads and refreshes a session, which is a hot path. Redis key TTLs give automatic expiry and cleanup. Redis has atomic counters for the rate limit.
- Cost: one new service to run, monitor and back up. Persistence (AOF, fsync every second) is on, so a Redis restart loses at most about 1 second of writes rather than logging everyone out.
- Rejected alternative: Postgres tables. This needs no new infrastructure, and it is a valid fallback if the team will not run Redis. It would add a write on every request and need a cleanup job. It is not recommended.

**2. Session record.**
- Key `sess:<id>`, a Redis hash with `user_id`, `created_at` and `expires_at` (see rule 3 for how it is set).
- The ID is 32 bytes from a CSPRNG, base64url encoded (256 bits). It is opaque and carries no user data.
- Only a hash of the ID is used as the key: `sess:<sha256(id)>`. A Redis dump or read access then does not yield usable session cookies.
- Cookie: `sid=<id>; HttpOnly; Secure; SameSite=Lax; Path=/`. There is no Domain attribute, so the cookie is host-only.
- Clearing the cookie sends the same attributes with `Max-Age=0`.

**3. Expiry: checked and recorded on the server by Redis.**
- `created_at` is stored on the record. Expiry is enforced on every request by Redis itself, with a TTL as the single source of truth.
- Idle rule: on every valid request, run one atomic step (a Lua script or `EXPIRE`) that sets the key TTL to `min(30 min, created_at + 12 h - now)`.
- Because of the `min`, the TTL never extends past the 12-hour cap. Each request restarts the 30-minute clock, up to that cap.
- At login the TTL is 30 minutes.
- The app also compares `now` to `created_at + 12 h` in code. This is a safety net in case the TTL arithmetic is wrong, and the session is treated as expired if the check fails.
- A key that Redis has already expired reads as "unknown", which is handled the same as "missing".
- All times come from the Redis server clock (`TIME`), so the two app instances cannot disagree.

**4. Abandoned sessions.**
- Redis removes them itself when the TTL lapses (lazy deletion plus its background sweep). No cron job and no cleanup code are needed.
- There is no per-user session index, because the requirements don't need "log out everywhere". Add one if that is wanted later.

**5. Failure counts and lockout (per lowercase email).**
- Key `fail:<email>` holds a sorted set of attempt timestamps (the sliding-window version of "5 in any 10 minutes").
- A single Lua script does everything for one failure: it removes entries older than 10 minutes, adds the new one, and counts the entries.
- When the count reaches 5 it sets `lock:<email>` with a 15-minute TTL.
- The `fail:` key gets a 10-minute TTL so it cleans itself up.
- Before the password check, the app tests whether `lock:<email>` exists. If it does, respond 429 immediately without touching bcrypt.
- A successful login deletes `fail:<email>`. `lock:<email>` cannot exist at that point, because a locked email never reaches the password check.
- Counting is by email, as required, and it also applies to emails that don't exist. This is deliberate: the unknown-email path then behaves the same as a real one, with no tell.
- Because `lock:<email>` is keyed only on the string, an attacker can lock out a real user by sending 5 bad attempts. This is inherent in the requirement. It is accepted here, and the abuse risk is noted for the reviewer.
- A locked unknown email and a locked real email both get the same 429. The 429 therefore reveals nothing about whether an account exists.

**6. Credential check and no account enumeration.**
- The email is lowercased and trimmed before use. It is also length-capped (for example 254 characters) so oversized input cannot create huge Redis keys.
- If the email is unknown, the app still runs a bcrypt compare against a fixed dummy hash with the same cost factor as real hashes. The timing of the unknown-email and wrong-password paths then matches.
- Unknown email and wrong password both produce the same single response: 401 with the login page showing "Invalid email or password". The body is the same, and the failure is recorded the same way.
- The lockout response (429) is only reachable by sending 5 failures, and it is the same for any email string.

**7. Session fixation.**
- On a successful login the server always generates a new ID. It never reuses the ID from the incoming cookie.
- If the request carried a cookie, the old session record is deleted before the redirect is sent.
- Order: create the new session, delete the old session, then reply with `Set-Cookie` and a 302 to `/dashboard`.

**8. Storage failure behavior (fail closed).**
- If Redis is unreachable or times out (a short timeout, for example 200 ms, and no retries on the request path):
  - A protected request is not allowed through. The user sees a plain 503 "Service temporarily unavailable, please try again" page. The session cookie is not cleared, because the session may well still be valid when Redis returns.
  - Login returns 503 with the same message. The lockout check cannot be done, so the password is not checked either. This avoids bypassing the brute-force limit when the limiter is down.
  - Logout returns 503. If the user clicks again later it still works. The cookie is cleared on that reply anyway, but the page tells the user that sign-out could not be confirmed. (The server-side session survives until its TTL, at most 30 minutes idle.)
- Redis failure never produces an "open" state in which unauthenticated users see protected pages.
- Errors are logged server-side with no session IDs in the log lines.

**9. Other rules.**
- State-changing form posts use SameSite=Lax. Lax already blocks the cookie on cross-site POSTs, which protects `/logout` and other posts from CSRF. A CSRF token is optional extra hardening and out of scope here.
- Responses for `/login`, `/logout` and every protected page send `Cache-Control: no-store`.
- Protected requests use one middleware that runs before every route except `GET /login` and `POST /login`.
- `GET /login` shows the form. If a valid session already exists, it can redirect to `/dashboard`.

## Rules for the diagram

- "Redis" means the shared store. "App" is whichever instance the load balancer picks. Any instance can serve any step.
- `fail:`, `lock:` and `sess:` are the keys from the decisions above.
- Each protected request does one atomic lookup-and-extend, not a read followed by a separate write.

## Sequence diagram

```mermaid
sequenceDiagram
    autonumber
    actor B as Browser
    participant A as App (either instance)
    participant R as Redis
    participant D as Postgres (users)

    Note over B,D: LOGIN POST /login (email, password)
    B->>A: POST /login (email, password, optional old sid cookie)
    A->>A: lowercase and trim email

    A->>R: EXISTS lock:email
    alt Redis unreachable
        A-->>B: 503 "Service temporarily unavailable" (no password check)
    else locked (5 failures in 10 min, lock lasts 15 min)
        R-->>A: yes
        A-->>B: 429 (password NOT checked)
    else not locked
        R-->>A: no
        A->>D: SELECT id, password_hash WHERE email
        alt unknown email
            D-->>A: no row
            A->>A: bcrypt compare against dummy hash (same timing)
        else user found
            D-->>A: id, password_hash
            A->>A: bcrypt compare
        end

        alt bad credentials (unknown email OR wrong password)
            A->>R: Lua: drop entries older than 10 min, add now to fail:email, count
            Note right of R: if count reaches 5, SET lock:email with 15 min TTL
            A-->>B: 401 login page "Invalid email or password"
        else success
            A->>R: create sess:hash(newId) {user_id, created_at}, TTL 30 min
            opt request carried an old sid
                A->>R: DEL sess:hash(oldId)
            end
            A->>R: DEL fail:email
            A-->>B: 302 /dashboard, Set-Cookie sid=newId (HttpOnly, Secure, SameSite=Lax)
        end
    end

    Note over B,D: PROTECTED PAGE (every route except /login)
    B->>A: GET /dashboard (sid cookie)
    alt no cookie
        A-->>B: 302 /login, clear cookie
    else cookie present
        A->>R: atomic: GET sess:hash(sid); if found and now < created_at + 12h then EXPIRE min(30 min, created_at + 12h - now)
        alt Redis unreachable
            A-->>B: 503 page (cookie kept)
        else missing, unknown, or expired (TTL lapsed or 12h passed)
            R-->>A: nil or expired
            opt 12h passed but key still exists
                A->>R: DEL sess:hash(sid)
            end
            A-->>B: 302 /login, clear cookie
        else valid
            R-->>A: user_id (idle clock restarted)
            A-->>B: 200 page for user_id
        end
    end

    Note over B,D: LOGOUT POST /logout
    B->>A: POST /logout (sid cookie, may be absent)
    opt cookie present
        A->>R: DEL sess:hash(sid)
    end
    alt Redis unreachable
        A-->>B: 503 "Could not confirm sign-out, try again"
    else deleted, or no session, or already gone
        A-->>B: 302 /login, clear cookie (same response in every case)
    end
```

## Notes on the diagram

- **Same reply for every logout.** Whether the session existed, was already expired, or never existed, the reply is the same 302 and cookie clear. Deleting a missing key in Redis is a harmless no-op.
- **Delete before reply.** On logout the server-side delete happens before the response is sent, as required. A copied cookie therefore stops working immediately.
- **Order at login.** The new session is created before the old one is deleted. If something fails in the middle, the user ends up with at most an extra session that expires by TTL, never with a half-logged-in state.
- **Lockout window.** Failures use a sliding window over the last 10 minutes. The lock lasts a fixed 15 minutes from the 5th failure, and attempts during the lock are not counted or extended.
- **Non-goals.** There is no sign-up, password reset, "remember me", or multi-session management. IP-based limits are not requested and are not included, so one attacker can try many emails at 4 attempts each. That is a known gap for the reviewer to weigh.
- **Open points for the reviewer.** (1) Approve adding Redis with persistence. (2) Accept that lockout by email lets someone lock out a known user. (3) Accept fail-closed 503s when Redis is down.
