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