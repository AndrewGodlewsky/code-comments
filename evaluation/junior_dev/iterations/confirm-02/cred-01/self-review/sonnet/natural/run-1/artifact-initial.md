# Personal API tokens: design and sequence diagram

## Where state lives

| State | Location | Notes |
|---|---|---|
| Token plaintext | The server's memory during the create request, then the browser's dialog state | It is never written to Postgres, logs or analytics. It exists only in the create response. Closing the dialog clears it from the page. |
| Token hash and metadata | Postgres table `api_tokens` | Columns: `id`, `user_id`, `name`, `token_hash` (SHA-256, unique index), `created_at`, `expires_at` (= `created_at` + 90 days), `revoked_at`, `last_used_at`. |
| Whether a token is valid | Postgres only | No cache in the server or the browser. Every token request reads the row. |
| Login session | Existing session store | Unchanged. |

"Active" means `revoked_at IS NULL AND expires_at > now()`. Every query uses the database clock.

## Decisions behind the diagram

- **Limit and name uniqueness.** A `now()` expression can't go in an index predicate, so a partial unique index can't express "unique among active tokens". Create runs in one transaction that first locks the user's row with `SELECT ... FOR UPDATE`. It then counts active tokens, checks the name among active tokens and inserts. Two concurrent creates for one user are serialised, so neither the 10-token limit nor the name rule can be raced.
- **Last-used without a write per request.** The lookup already reads the row and returns a `stale` flag, computed by the database as `last_used_at IS NULL OR last_used_at < now() - interval '1 hour'`.
  - A write happens only when `stale` is true. That is at most one write per token per hour.
  - The write is guarded by the same condition, so concurrent requests produce one effective write.
  - It runs after the response is sent. If it fails, the failure is logged without the token and the request is unaffected.
  - The displayed value is therefore under 1 hour out of date. It survives restarts, because no in-memory buffer is involved.
- **Revoke takes effect on the next request.** Revoke sets `revoked_at = now()` in a single `UPDATE`, and the auth lookup requires `revoked_at IS NULL` on every call. The system has one server and one database, so the next read sees the commit.
- **Ownership.** The revoke `UPDATE` has `WHERE id = $1 AND user_id = $session_user`. The list query filters on `user_id`. Someone else's token id gives the same 404 as an unknown id.
- **Token routes accept session cookies only.** A Bearer token cannot list, create or revoke tokens, so a leaked token cannot mint new ones.
- **Token generation.** `pat_` plus 32 characters from the CSPRNG. The server uses base62 with rejection sampling, to avoid modulo bias. The create response sends `Cache-Control: no-store`. Response-body logging is switched off for this route.
- **Uniform 401.** A missing header, malformed value, unknown hash, revoked token and expired token all return the same status, headers and body. The lookup is one query that cannot tell the cases apart. The server may log an internal reason code, never the token.
- **Lost create response.** The server cannot replay the token, because it does not have it. Replaying would need plaintext storage, which is forbidden. The row exists and counts toward the limit of 10. The user sees it in the list, with "Never" as last used, revokes it and creates a new one. A retry with the same name returns 409, and the message says to revoke the existing token or choose another name.

## Sequence diagram

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant B as Browser (Account Settings)
    participant S as Web/API server
    participant D as Postgres (api_tokens)
    participant C as API client (script or CI)

    %% ============ FLOW 1: CREATE ============
    rect rgb(235, 245, 255)
    Note over U,D: FLOW 1 - Create a token
    U->>B: Enter name, click Create
    B->>S: POST /settings/tokens (session cookie, name)
    S->>S: Existing session check, session user becomes user_id
    alt not signed in
        S-->>B: 401 (existing login behaviour)
    else name is empty or longer than 40 characters
        S-->>B: 400 name must be 1 to 40 characters
    else name is valid
        S->>S: Generate pat_ plus 32 CSPRNG characters, compute SHA-256 hash
        Note right of S: Plaintext lives only in this request's memory
        S->>D: BEGIN, SELECT user row FOR UPDATE (serialises this user's creates)
        S->>D: Count active tokens, check name among active tokens
        D-->>S: count and name_taken
        alt count is 10 or more
            S->>D: ROLLBACK
            S-->>B: 409 Limit reached, revoke a token first
            B-->>U: Show message
        else name already used by an active token
            S->>D: ROLLBACK
            S-->>B: 409 Name in use, choose another or revoke that token
        else room available and name free
            S->>D: INSERT user_id, name, token_hash, created_at=now(), expires_at=now()+90 days
            S->>D: COMMIT
            Note right of D: Only the hash is stored
            alt response reaches the browser
                S-->>B: 201 token plaintext once, plus id and dates (Cache-Control no-store)
                B-->>U: Dialog shows token with Copy button
                U->>B: Close dialog
                B->>B: Discard token from page state
                Note over B,S: Nobody can show it again, including support and engineering
            else response lost (network drop or tab closed)
                S--xB: 201 never arrives
                Note over B,D: Row is committed and counts toward the limit of 10, but the plaintext is gone. The user finds it in the list (Never used), revokes it and creates a new one. Retrying with the same name gets 409.
            end
        end
    end
    end

    %% ============ FLOW 2: LIST ============
    rect rgb(240, 250, 240)
    Note over U,D: FLOW 2 - List tokens
    U->>B: Open Account Settings
    B->>S: GET /settings/tokens (session cookie)
    alt not signed in
        S-->>B: 401 (existing login behaviour)
    else signed in
        S->>D: SELECT id, name, created_at, expires_at, last_used_at WHERE user_id = session user AND revoked_at IS NULL AND expires_at > now()
        D-->>S: rows (never token_hash, never plaintext)
        S-->>B: 200 list
        B-->>U: Name, created, expires, last used (null shown as Never)
        Note over B,D: last_used_at may be up to 1 hour old
    end
    end

    %% ============ FLOW 3: API CALL ============
    rect rgb(255, 248, 230)
    Note over C,D: FLOW 3 - API call authenticated by a token, with last-used recording
    C->>S: GET /api/anything, Authorization Bearer TOKEN
    S->>S: Parse header, reject if missing or not pat_ plus 32 characters
    S->>S: SHA-256 hash of presented token
    S->>D: SELECT id, user_id, stale FROM api_tokens WHERE token_hash = hash AND revoked_at IS NULL AND expires_at > now()
    Note right of D: stale = last_used_at IS NULL OR last_used_at older than 1 hour. No cache, every request reads the row.
    D-->>S: row or no row
    alt header missing or malformed, or no row (unknown, revoked or expired)
        S-->>C: 401 same status, headers and generic body in every case
        Note right of S: Internal log has a reason code only, never the token
    else row found
        S->>S: Run request as user_id
        S-->>C: Normal response
        opt stale is true (at most about once per hour per token)
            S->>D: UPDATE SET last_used_at = now() WHERE id = token id AND (last_used_at IS NULL OR last_used_at older than 1 hour)
            Note right of S: After the response, a failure is logged and ignored. The guard means concurrent requests cause one write.
        end
        Note over S,D: When stale is false there is no database write
    end
    end

    %% ============ FLOW 4: REVOKE ============
    rect rgb(255, 238, 238)
    Note over U,D: FLOW 4 - Revoke a token
    U->>B: Click Revoke on a token
    B-->>U: Confirmation dialog
    alt user cancels
        U->>B: Cancel
        Note over B: Nothing is sent
    else user confirms
        U->>B: Confirm
        B->>S: DELETE /settings/tokens/ID (session cookie)
        alt not signed in
            S-->>B: 401 (existing login behaviour)
        else signed in
            S->>D: UPDATE SET revoked_at = now() WHERE id = ID AND user_id = session user AND revoked_at IS NULL
            D-->>S: rows affected
            alt 0 rows (unknown id, someone else's token, or already revoked)
                S-->>B: 404 (no hint whether the id exists for another user)
                B-->>U: Refresh list
            else 1 row
                S-->>B: 204
                B-->>U: Token removed from list
                C->>S: Next API request with that token
                S->>D: Lookup (Flow 3)
                D-->>S: no row (revoked_at is set)
                S-->>C: 401 generic
            end
        end
    end
    end
```

## Failure summary

| Situation | Result | State afterwards |
|---|---|---|
| 11th token requested | 409 with "revoke a token first" | Nothing inserted |
| Name invalid or already used by an active token | 400 or 409 | Nothing inserted |
| Database error during create | 500, no token in the response | Transaction rolled back, nothing stored |
| Create response never reaches the browser | The user sees no token | Row exists and counts toward the limit. The user revokes it from the list and creates a new one. |
| Missing, unknown, revoked or expired Bearer token | Identical 401 | No state change |
| `last_used_at` update fails | The API request still succeeds | Last-used stays stale until the next stale request |
| Revoke of another user's or an unknown token | 404 | No state change |

## Assumptions to confirm

- The existing session middleware already protects state-changing settings routes against CSRF. If it doesn't, add that before shipping.
- A single-column unique index on `token_hash` and an index on `(user_id)` are enough at this scale.
- Expired and revoked rows stay in the table, with no cleanup job in this scope. They don't count toward the limit and don't block reuse of a name.
