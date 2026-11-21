# Personal API tokens on Account Settings: sequence design

## Decisions before the diagram

- **Token format.** `pat_` followed by 32 characters from a 62-character alphabet (A-Z, a-z, 0-9). That is about 190 bits. Characters come from a CSPRNG with unbiased sampling.
- **Stored fields.** `api_tokens` holds `id`, `user_id`, `name`, `token_hash` (SHA-256, unique index), `created_at`, `expires_at`, `revoked_at` and `last_used_at`. No column holds the plaintext.
- **Active is computed, not stored.** A token is active when `revoked_at` is null and `expires_at` is after now. Limit and name checks use this same definition, so expiry needs no background job to be correct.
- **Name uniqueness is enforced in the transaction, not by a unique index.** A plain unique index on (user, name) would block reusing the name of a revoked or expired token. Create takes a row lock on the user row, so two concurrent creates cannot exceed 10 tokens or take the same name.
- **Validity is read on every request.** Bearer auth looks up `token_hash` in Postgres on each call and reads from the primary. Nothing caches validity, so the first request after a revoke commits gets a 401.
- **Last-used is buffered.** Each authenticated request writes the token id and time into an in-memory map that keeps the latest time per token. A timer flushes the map every 5 minutes in one batched `UPDATE` using `GREATEST`, so a flush never moves the timestamp backwards and ignores `revoked_at`. Staleness stays within the 1-hour allowance. A crash loses at most one interval of updates.
- **Lost create response (judgment call).** The server commits the row before it responds. If the response never reaches the browser, the token is active, cannot be recovered and counts toward the limit until revoked or expired. It does appear in the list by name, so the user can revoke it. A pending state with a browser acknowledgement would avoid the orphan, but it adds a state and a round trip. This design defers that unless orphans prove to be a real problem.

## Sequence diagram

```mermaid
sequenceDiagram
    participant B as Browser
    participant C as API client
    participant A as API server
    participant M as Server memory
    participant D as Postgres

    Note over B,D: Flow 1 - Create a token
    B->>A: POST /settings/tokens with name and session cookie
    A->>A: Check session and name length 1 to 40 after trim
    alt Name invalid
        A-->>B: 400 with name rules
    else Name valid
        A->>D: BEGIN and lock the users row FOR UPDATE
        A->>D: Count active tokens and check whether name is taken
        alt Already 10 active tokens
            A->>D: ROLLBACK
            A-->>B: 409 limit reached, revoke a token first
        else Name used by an active token
            A->>D: ROLLBACK
            A-->>B: 409 name already in use
        else Within limit and name free
            A->>A: Generate pat_ plus 32 CSPRNG characters and hash with SHA-256
            A->>D: INSERT hash, name, created_at and expires_at set to created_at plus 90 days
            D-->>A: COMMIT ok, row is active
            alt Response reaches browser
                A-->>B: 201 with full token, shown once
                Note over B: Dialog shows token with Copy button, closing it drops the token
            else Response lost in transit
                A--xB: 201 never arrives
                Note over B: Browser shows status unknown, token cannot be recovered
                B->>A: Later, GET list
                A-->>B: Token listed by name only, revoke it to free a slot
            end
        end
    end

    Note over B,D: Flow 2 - List tokens
    B->>A: GET /settings/tokens with session cookie
    A->>D: SELECT name, created_at, expires_at, last_used_at for this user where not revoked and expires_at is after now
    D-->>A: Active rows only
    A-->>B: 200 list, null last_used shown as Never, no token value or hash

    Note over C,D: Flow 3 - API call authenticated by a token
    C->>A: GET /api/resource with Authorization Bearer pat_ token
    A->>A: Check Bearer format
    alt Header missing or malformed
        A-->>C: 401 generic body
    else Format ok
        A->>A: SHA-256 the token, token is never logged
        A->>D: SELECT user_id, expires_at, revoked_at WHERE token_hash matches, primary read, no cache
        D-->>A: Row or no row
        alt No row, revoked, or expired
            A-->>C: 401 same generic body and same headers
        else Active
            A->>M: Record token id and now, keep the latest time
            A->>A: Run request as the token owner
            A-->>C: 200 response
        end
    end
    loop Every 5 minutes, inside the server process
        M->>D: One batched UPDATE of last_used_at using GREATEST, ignores revoked_at
    end

    Note over B,D: Flow 4 - Revoke a token
    B->>B: User clicks Revoke and confirms
    B->>A: POST /settings/tokens/TOKEN_ID/revoke with session cookie
    A->>D: UPDATE set revoked_at to now where id matches, owner is session user, and revoked_at is null
    alt One row updated
        D-->>A: 1 row
        A-->>B: 204, row removed from list
    else Zero rows
        D-->>A: 0 rows
        A-->>B: 404, or 204 if it was already revoked
    end
    Note over C,D: Next API call with the same token
    C->>A: GET /api/resource with the same token
    A->>D: SELECT by token_hash on primary
    D-->>A: Row with revoked_at set
    A-->>C: 401 generic body
```

## Where state lives

| State | Location | Lifetime and rule |
|---|---|---|
| Plaintext token | Server memory during the create request, the 201 body, and browser dialog memory | Until the dialog closes or the response is discarded. Never in the DB, logs or analytics. |
| Hash, name, created, expires, revoked | Postgres `api_tokens` | Rows kept for audit. Retention is not decided. |
| Last used | Server memory map, then `api_tokens.last_used_at` after each flush | Memory holds at most 5 minutes of updates. |
| Limit and name checks | Derived from `api_tokens` inside the create transaction | Computed per request, under the user row lock. |
| Token validity | Derived from `api_tokens` on each API call | No cache. |
| Browser state | None persistent. No localStorage. The list never returns a token. | Gone on reload. |

## Failure behaviour

| Failure | Server result | Browser shows | State afterwards |
|---|---|---|---|
| Name invalid | 400 | Field error | Nothing written |
| 11th active token | 409, revoke a token first | Limit message | Nothing written |
| Name in use | 409 | Name error | Nothing written |
| DB error during create | 500, rollback | Generic error, retry | No row |
| Create response lost | 201 sent but not received | Status unknown, check the list | Row active, token unrecoverable, counts toward limit until revoked or expired |
| Bad token (missing, malformed, unknown, revoked, expired) | 401, same body and `WWW-Authenticate` header in every case | Not applicable to API clients | Nothing changes |
| Revoke DB error | 500 | Not revoked, retry | Token stays active. UI must not show it as revoked. |
| Revoke of another user's token | 404 | Not found | Nothing changes |
| Last-used flush fails | Logged, entries kept and retried next interval | Nothing | Last used stale a little longer |
| Crash before flush | None | Nothing | Last used lost for up to one interval |

## Checks before build

- **Log redaction.** Strip the `Authorization` header and the create response body from request logs and error traces. Never log the token or its hash. Analytics events carry only token id and user id.
- **Read routing.** Bearer validation must read from the primary, or from a replica with a lag guarantee. A lagging replica would let a revoked token pass.
- **Route scope.** The brief does not say which routes accept bearer tokens. Assumed: REST API routes accept them, and session-only settings routes do not. This needs confirmation.
- **CSRF.** The three settings endpoints assume the existing settings CSRF protection applies. The brief does not cover this.
- **Failed-auth rate limit.** Not in the brief. Recommended, so unknown-token guessing is throttled per IP.
- **Orphan tokens.** Monitor how often a lost create response leaves an unseen active token. Revisit the pending-state option only if it causes real limit complaints.