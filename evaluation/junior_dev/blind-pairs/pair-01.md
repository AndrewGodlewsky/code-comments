# Pair 01

Which document would a smart engineer who does not know this project understand faster and more correctly?

---

# Document A

# Personal API tokens on Account Settings: sequence design

## What this is

Signed-in users create named personal API tokens on Account Settings, so scripts and CI jobs can call the REST API without a password. Session-cookie login already works, and the settings endpoints sit behind it. The system is one web/API server with one Postgres database, and there is no token table yet. Each API call checks its token against Postgres, so a revoke takes effect on the next request. The last-used time is kept in server memory and written in batches every 5 minutes, so the API does not write to the database on every call.

## Terms

- **Token**: a secret string, `pat_` followed by 32 random characters. It is shown once, when created.
- **Session**: the login cookie from the existing sign-in. Every settings call needs a valid one.
- **Hash**: the SHA-256 output of a token. The database stores the hash and finds a token by it. The token itself is never stored.
- **Active**: not revoked and not expired. Only active tokens count toward the limit and appear in the list. It is computed from `revoked_at` and `expires_at` on each check, so expiry needs no background job.
- **Revoke**: mark a token as revoked by setting `revoked_at`. The row stays in the table.
- **Bearer header**: `Authorization: Bearer <token>`, the header API clients send with each call.
- **CSPRNG**: a random number source built for secrets (cryptographically secure).
- **Unique index**: a database rule that stops two rows from holding the same value in the given columns.
- **Row lock**: `SELECT ... FOR UPDATE` on the user's row, so two create requests for the same user run one at a time.
- **Primary**: the Postgres server that accepts writes. Checks that must see the newest change read from it.
- **Last used**: the most recent time a token was used.
- **Flush**: saving the buffered last-used times to the database.
- **Snapshot**: the buffered times taken out of memory for one flush.
- **GREATEST**: a Postgres function that returns the larger of its inputs.
- **CSRF**: cross-site request forgery, an attack where another site makes the browser send a request with the user's cookie.

## Diagram

```mermaid
sequenceDiagram
    participant B as Browser
    participant C as API client
    participant A as API server
    participant M as Server memory
    participant D as Postgres

    Note over B,D: Flow 1 - Create a token
    B->>A: POST /settings/tokens with name and session cookie
    alt No valid session
        A-->>B: 401
    else Session valid
        A->>A: Trim name and check 1 to 40 characters
        alt Name invalid
            A-->>B: 400 with name rules
        else Name valid
            A->>D: BEGIN and lock the user row FOR UPDATE
            A->>D: Count active tokens and check whether name is used by an active token
            alt 10 active tokens already
                A->>D: ROLLBACK
                A-->>B: 409 limit reached, revoke a token first
            else Name used by an active token
                A->>D: ROLLBACK
                A-->>B: 409 name already in use
            else Limit and name OK
                A->>A: Generate pat_ plus 32 CSPRNG characters and hash with SHA-256
                A->>D: INSERT id made by database, user_id from session, name, token_hash, created_at, expires_at = created_at plus 90 days, revoked_at null, last_used_at null, then COMMIT
                D-->>A: COMMIT ok, row is active
                alt Response reaches browser
                    A-->>B: 201 with full token, shown once
                    Note over B: Dialog shows token with Copy button, closing it means nobody can show it again
                else Response lost in transit
                    A--xB: 201 never arrives
                    Note over B: Browser shows status unknown, no automatic retry
                    B->>A: Later, GET list
                    A-->>B: Token listed by name only, revoke it to free a slot
                end
            end
        end
    end

    Note over B,D: Flow 2 - List tokens
    B->>A: GET /settings/tokens with session cookie
    alt No valid session
        A-->>B: 401
    else Session valid
        A->>D: SELECT id, name, created_at, expires_at, last_used_at for this user where active
        D-->>A: Active rows only
        A-->>B: 200 list, null last_used shown as Never, never a token or hash
    end

    Note over C,D: Flow 3 - API call with a token
    C->>A: GET /api/resource with Authorization Bearer pat_ token
    alt Header missing or not pat_ plus 32 characters
        A-->>C: 401 generic body and WWW-Authenticate header
    else Format OK
        A->>A: SHA-256 the token, never log the token or its hash
        A->>D: SELECT user_id, expires_at, revoked_at WHERE token_hash matches, primary read, no cache
        alt Lookup error or timeout
            D--xA: No answer
            A-->>C: 500 generic body, request not run
        else Lookup answered
            D-->>A: Row or no row
            alt No row, revoked, or expired
                A-->>C: 401 same generic body and same header
            else Active
                A->>M: Record token id and now, keep the latest time per token
                A->>A: Run request as the token owner, with the owner's full rights
                A-->>C: 200 response
            end
        end
    end
    loop Every 5 minutes, inside the server process
        M->>M: Swap live map for an empty map, keep the old map as snapshot
        M->>D: One batched UPDATE by token id, last_used_at = GREATEST(last_used_at, snapshot time), does not check revoked_at
        alt UPDATE committed
            M->>M: Drop snapshot
        else UPDATE failed
            M->>M: Merge snapshot back into live map, keep later time per token
        end
    end

    Note over B,D: Flow 4 - Revoke a token
    B->>B: User clicks Revoke and confirms
    B->>A: POST /settings/tokens/TOKEN_ID/revoke with session cookie
    alt No valid session
        A-->>B: 401
    else Session valid
        A->>D: UPDATE set revoked_at to now WHERE id matches, user_id is session user, revoked_at is null
        alt One row updated
            D-->>A: 1 row
            A-->>B: 204, row removed from list
        else Zero rows
            D-->>A: 0 rows
            A->>D: SELECT the token WHERE id matches and user_id is session user
            alt Token belongs to this user, already revoked
                A-->>B: 204, nothing changes
            else Unknown or another user's token
                A-->>B: 404, nothing changes
            end
        end
    end
    Note over C,D: Next API call with the same token
    C->>A: GET /api/resource with the same token
    A->>D: SELECT by token_hash on primary
    D-->>A: Row with revoked_at set
    A-->>C: 401 generic body
```

## Notes on the diagram

**Session.** Every settings call checks the session cookie first. A missing or invalid session gets 401, not a redirect, because these are page calls rather than browser navigations. The session is the existing login. Where it is stored does not change this design.

**Create (Flow 1).**
- Trigger: the user submits a name in the dialog.
- The name is trimmed and must be 1 to 40 characters. Otherwise the server returns 400 and writes nothing.
- The lock, the count and the name check run in one transaction. Two concurrent creates therefore cannot exceed 10 active tokens or take the same name.
- Name uniqueness is enforced in the transaction, not by a unique index on (user, name). That index would block reusing the name of a revoked or expired token.
- The token is `pat_` plus 32 characters from a 62-character alphabet (A-Z, a-z, 0-9). The characters come from a CSPRNG with unbiased sampling, which gives about 190 bits. Only the SHA-256 hash is stored.
- The row is inserted with these values:
  - `id` is made by the database.
  - `user_id` comes from the session, never from the request body.
  - `name`, `token_hash`, `created_at` as the insert time, and `expires_at` as `created_at` plus 90 days.
  - `revoked_at` and `last_used_at` are null.
- A token expires 90 days after creation and cannot be renewed.
- A user may have 10 active tokens. The 11th create is refused with a message to revoke a token first.
- Expired and revoked rows are never deleted. They stop counting toward the limit and stop appearing in the list.

**Lost create response.** The row is committed before the 201 is sent. The browser shows "status unknown" after a network error or when no response arrives. The brief sets no timeout, which is an open question. The browser does not retry the POST by itself. A retry would hit the name check and show a misleading "name in use" error for a token that already exists. If the response is lost, the token is active and cannot be recovered. It counts toward the limit until revoked or expired. It appears in the list by name, so the user can revoke it. A pending state with a browser acknowledgement would avoid this orphan, but it adds a state and a round trip. That option is deferred unless orphans prove to be a real problem.

**List (Flow 2).** The list returns only this user's active tokens: name, created date, expiry date and last-used time. A token never used shows "Never". The list never returns the token or its hash. Last-used may be up to 1 hour out of date.

**Bearer call (Flow 3).**
- The server first checks the Bearer format. A missing or malformed header gets 401 with the generic body and the `WWW-Authenticate` header.
- It hashes the token with SHA-256. The token and its hash are never logged.
- It reads the row by `token_hash` from the primary, with no cache. A cache could let a revoked token pass after the revoke commits.
- If the lookup errors or times out, the server returns 500 with a generic body and does not run the request. It is not a 401, because the token was never checked. A database error never lets a token through.
- No row, a revoked row or an expired row gets 401 with the same body and header. The response does not say which case it was.
- An active token is recorded in memory as the token id and the current time. The request then runs as the token owner. The brief defines no scopes, so the token has the same rights as its user.

**Last-used flush.** Every 5 minutes, inside the one server process:
1. The server swaps the live map for an empty map. The old map becomes the snapshot. Calls made during the write go into the new map and wait for the next interval.
2. One batched UPDATE names each row by token id and sets `last_used_at = GREATEST(stored value, snapshot time)`. A flush never moves a time backwards. The UPDATE does not check `revoked_at`.
3. If the UPDATE commits, the snapshot is dropped.
4. If the UPDATE fails, the snapshot is merged back into the live map, keeping the later time for each token. The next interval retries. No time is lost, and none moves backwards.

Staleness stays within the 1-hour allowance in the brief. A crash loses at most one interval of updates. The brief names one server, so one process holds the map. If more instances were added, each would flush its own times. GREATEST would still keep the rows correct, but a crash would still lose that instance's unflushed times.

**Revoke (Flow 4).**
- The user clicks Revoke and confirms. The browser sends the request with the session cookie.
- The UPDATE changes only an active row owned by the session user.
- If one row changes, the server returns 204 and the row leaves the list.
- If zero rows change, one SELECT checks whether the id belongs to this user. If it does and it is already revoked, the answer is 204, so a repeated revoke is harmless. If the id is unknown or belongs to another user, the answer is 404. Both cases look the same, so another user's tokens cannot be detected.
- If the UPDATE fails, the server returns 500. The token stays active, and the UI must not show it as revoked.
- The next API call with the token gets 401. The lookup reads `revoked_at` on the primary with no cache, so the first request after the revoke commits is refused.

## Where state lives

| State | Location | Lifetime and rule |
|---|---|---|
| Plaintext token | Server memory during the create request, the 201 body, browser dialog memory | Until the dialog closes or the response is dropped. Never in the DB, logs or analytics. |
| Id, user, hash, name, created, expires, revoked | Postgres `api_tokens` | Rows are kept for audit. Retention is not decided. |
| Last used | Server memory map, plus a snapshot while a flush runs, then `api_tokens.last_used_at` after each flush | Memory holds at most 5 minutes of updates, plus one snapshot while a flush writes. |
| Limit and name checks | Derived from `api_tokens` inside the create transaction | Computed per request, under the user row lock. |
| Token validity | Derived from `api_tokens` on each API call | No cache. |
| Browser state | None persistent, no localStorage | The list never returns a token. Gone on reload. |

## What happens when things fail

| Failure | Server result | Browser shows | State afterwards |
|---|---|---|---|
| No valid session on any settings call | 401 | Sign in again | Nothing written |
| Name invalid | 400 | Field error | Nothing written |
| 11th active token | 409, revoke a token first | Limit message | Nothing written |
| Name in use by an active token | 409 | Name error | Nothing written |
| DB error during create | 500, rollback | Generic error, retry | No row |
| Create response lost | 201 sent, not received | Status unknown, check the list | Row active, token unrecoverable, counts toward limit until revoked or expired |
| Bad token (missing, malformed, unknown, revoked, expired) | 401, same body and `WWW-Authenticate` header in every case | Not applicable to API clients | Nothing changes |
| Bearer lookup error or timeout | 500 generic body, request not run | Not applicable to API clients, retry later | Nothing changes |
| Revoke DB error | 500 | Not revoked, retry | Token stays active. UI must not show it as revoked. |
| Revoke of another user's or unknown token | 404 | Not found | Nothing changes |
| Last-used flush fails | Logged, snapshot merged back into memory, retried next interval | Nothing | Last used stale a little longer |
| Crash before flush | None | Nothing | Last used lost for up to one interval |

## Rollout checks

These are checks to make before building. They are not part of how the system runs.

- **Log redaction.** Strip the `Authorization` header and the create response body from request logs and error traces. Never log the token or its hash. Analytics events carry only token id and user id.
- **Read routing.** Bearer validation reads from the primary, or from a replica with a lag guarantee. A lagging replica would let a revoked token pass.
- **Route scope.** The brief does not say which routes accept bearer tokens. Assumed: REST API routes accept them, and session-only settings routes do not. Needs confirmation.
- **CSRF.** The three settings endpoints assume the existing settings CSRF protection applies. The brief does not cover it. Needs confirmation.
- **Failed-auth rate limit.** Not in the brief. Recommended, so guessing unknown tokens is throttled per IP.
- **Orphan tokens.** Monitor how often a lost create response leaves an unseen active token. Revisit the pending-state option only if it causes real limit complaints.

## Open questions

- Should a disabled or deleted user's tokens stop working? The brief does not say. If yes, the bearer lookup should also check the user row.
- How long should revoked and expired rows be kept? Not decided.
- How long should the browser wait before it reports a create as "status unknown"? The brief sets no timeout.

---

# Document B

# Personal API tokens on Account Settings: sequence diagram

**What this design does.** A signed-in user creates a personal API token on the Account Settings page. An API token is a long random password for scripts and CI jobs (automated build and test systems). The token starts with `pat_`. A script sends it in an `Authorization: Bearer <token>` header to call our REST API (the web addresses programs use to read and change data). The script never needs the user's password.

The server shows the full token one time, in the reply to the create request. After that, it can never show the token again, not even to support or engineers. A user who loses a token creates a new one.

The server stores only a SHA-256 hash of the token, in a new `api_tokens` table in Postgres (our database). A hash is a fixed fingerprint computed from the token. SHA-256 works in one direction only. To check a presented token, the server computes its fingerprint and compares it with the stored one. It cannot recover the token from the fingerprint.

Every API request reads the token's row, so a revoke takes effect on the very next request. The server keeps no cache of whether a token is valid. Each row also has a `last_used_at` column. The server writes that column at most once every 15 minutes per token. The displayed last-used time is therefore at most 15 minutes old, which is inside the 1 hour the brief allows. Busy scripts also do not cause a database write on every call.

Creates for the same user run one at a time. Each create runs in a transaction, a group of database steps that either all happen or none do. The first step locks that user's `users` row with `SELECT ... FOR UPDATE` (a row lock). A second create for the same user waits until the first one commits or rolls back. Without this lock, two creates could both pass the 10-token limit or both pass the name check.

**Terms used below**

- **Bearer token:** a credential. Whoever holds it can use it. No other proof is needed.
- **Hash (SHA-256):** a fixed-length fingerprint. The same token always gives the same fingerprint, but the fingerprint cannot be reversed.
- **CSPRNG:** a cryptographically secure random number generator. It is safe to use for secrets.
- **Idempotent:** running the same action twice has the same result as running it once.
- **Session cookie:** the login cookie the browser already sends to the settings pages. API clients do not use it.
- **Endpoint:** a URL the server answers to, such as POST /settings/tokens.
- **Status codes:** 400 means bad input. 401 means not authorized. 404 means not found. 409 means conflict, here a duplicate name. 422 means the request was refused by a rule, here the token limit.
- **Generic 401 body:** the same error text for every kind of bad token, so a caller cannot tell which check failed.

**Reading the diagram.** A solid arrow is a request. A dashed arrow is a response. `--x` marks a response that never arrives. `-)` marks a background write, which the API response does not wait for. An `alt` block is an either-or branch. An `opt` block happens only in some cases.

```mermaid
sequenceDiagram
    participant B as Browser (Account Settings)
    participant A as Web/API server
    participant DB as Postgres
    participant C as API client (script or CI)

    Note over B,DB: 1. Create a token
    B->>A: POST /settings/tokens with name and session cookie
    A->>A: Check session and check name is 1 to 40 characters
    alt Name invalid
        A-->>B: 400 invalid name
    else Name valid
        A->>DB: BEGIN transaction, then SELECT users row FOR UPDATE for this user
        Note right of DB: The row lock makes a second create for the same user wait, so the checks below cannot race
        A->>DB: Count active tokens and check whether an active token has this name
        alt Name taken, or 10 active tokens already
            A->>DB: ROLLBACK
            A-->>B: 409 name taken, or 422 limit reached, revoke a token first
        else Room available
            A->>A: Generate pat_ plus 32 random characters, token_hash = SHA-256 of the token
            A->>DB: INSERT row with user, name, token_hash, created_at, expires_at = created_at plus 90 days, last_used_at NULL, revoked_at NULL
            A->>DB: COMMIT
            alt Response delivered
                A-->>B: 201 with full token, the only time it is sent
                Note over B: Dialog shows the token with a Copy button. It is kept in memory only and is gone when the dialog closes
            else Response lost in transit
                A--xB: 201 with full token never arrives
                Note over B: Browser shows an error. The row is committed and counts toward the limit. The token can never be shown again, but the row appears in the list so the user can revoke it. The browser must not retry on its own
            end
        end
    end

    Note over B,DB: 2. List active tokens
    B->>A: GET /settings/tokens with session cookie
    A->>DB: SELECT id, name, created_at, expires_at, last_used_at for this user where not revoked and expires_at is in the future
    DB-->>A: Active rows only, no hash and no token
    A-->>B: 200 list, where a NULL last_used_at shows Never

    Note over C,DB: 3. API call with a token
    C->>A: Request with Authorization Bearer pat_ token
    alt Header missing or not Bearer
        A-->>C: 401 generic body
    else Header present
        A->>A: token_hash = SHA-256 of the presented token
        A->>DB: SELECT row WHERE token_hash matches, on every request, no cache
        alt No row, revoked, or expired
            DB-->>A: no row, or revoked_at is set, or expires_at is in the past
            A-->>C: 401 same generic body
        else Valid
            DB-->>A: row with user_id and last_used_at
            A-->>C: 200 normal API response, as that user
            opt last_used_at is NULL or older than 15 min
                A-)DB: UPDATE last_used_at = now() for this row
                Note right of DB: If this write fails, the error is logged without the token. The API response is unchanged and the next request tries the write again
            end
        end
    end

    Note over B,DB: 4. Revoke a token
    B->>B: Click Revoke, then confirm
    B->>A: POST /settings/tokens/ID/revoke with session cookie
    A->>DB: UPDATE row SET revoked_at = COALESCE(revoked_at, now()) WHERE id and user_id match the session user, RETURNING id
    alt Row returned (first or repeat revoke of own token)
        DB-->>A: id
        A-->>B: 200 revoked, the row leaves the list
    else No row (not found, or someone else's token)
        DB-->>A: 0 rows
        A-->>B: 404, same whether the token exists or not
    end
    Note over B: If this response is lost, the browser shows an error. Clicking Revoke again is safe because the call is idempotent. COALESCE keeps the first revoke time if there is one
    Note over C,DB: Next API request with that token
    C->>A: Request with the token
    A->>DB: SELECT row WHERE token_hash matches
    DB-->>A: revoked_at is set
    A-->>C: 401 generic body
```

**Where state lives**

| State | Location | Notes |
|---|---|---|
| Plaintext token | Browser memory, for the create dialog only | Never written to storage, logs, or analytics. Lost when the dialog closes. |
| Token hash, name, user, created, expires, last used, revoked | Postgres `api_tokens` table | No plaintext column. `token_hash` is unique and indexed, so each API request finds its row quickly. |
| Per-user create lock | Postgres `users` row | Held only for the length of the create transaction. |
| Session identity | Session cookie | Used only by the settings endpoints. Token authentication never uses it. |
| Validity | Not cached anywhere | Each API request reads the row, so the first request after a revoke is rejected. |
| Request logs and analytics | Log and analytics stores | Record the token id and the outcome only. Never the Authorization header, the token, or its hash. |

**Failure handling**

| Failure | Result |
|---|---|
| 11th active token | 422. The message tells the user to revoke a token first. Nothing is written. |
| Name already used by an active token | 409. Nothing is written. A revoked or expired token does not block its name. |
| Create fails before COMMIT | The transaction rolls back. Nothing is stored, and the user can retry. |
| Create response lost after COMMIT | The server cannot tell whether the response arrived. A row exists, but its token can never be shown. The row counts toward the limit until the user revokes it or 90 days pass. A retry would create a second token, so the browser must not retry automatically. |
| Missing, malformed, unknown, revoked, or expired token | The same 401 status and generic body in every case, so the response does not reveal which check failed. |
| Revoke response lost | The browser shows an error. The token may already be revoked, so the user can click Revoke again. The call is idempotent, so a repeat is safe. |
| `last_used_at` write fails | Logged without the token. The API response is unchanged. The next request retries the write. |
| Request already in flight during revoke | May still succeed. The guarantee covers only requests that start after the revoke response returns. |

**Decisions and open items**

- **Write throttle (decided by this design).** The 15-minute interval is a choice made here, not something the brief sets. The displayed last-used time can be at most 15 minutes stale, inside the 1 hour the brief allows. The throttle compares against the `last_used_at` value stored in Postgres, not an in-memory timer. It therefore still works after a server restart.
- **Token format (assumed, needs confirmation).** The token is `pat_` followed by 32 characters. Each character is one of the 62 letters and digits (a to z, A to Z, 0 to 9). The server draws random bytes and throws away any byte from 248 to 255. This is needed because 256 does not divide evenly by 62, so keeping those bytes would make some characters slightly more likely than others. The brief does not fix the character set, so please confirm it.
- **Name uniqueness (assumed, needs confirmation).** The name check is an exact, case-sensitive match. So "CI" and "ci" are different names.
- **Token management endpoints (not decided by the brief).** The default is that the endpoints which create and revoke tokens accept only the session cookie, not API tokens. This means a leaked token cannot mint more tokens or revoke others.
- **Hashing (decided).** The token has about 190 bits of randomness. 62 to the power of 32 is about 2 to the power of 190. Guessing it is infeasible even for someone who has the hash, so plain SHA-256 is enough. Salted, slow hashes such as bcrypt protect human-chosen passwords, which can be guessed. They are not needed here.
