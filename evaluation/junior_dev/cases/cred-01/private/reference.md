**State.** One new Postgres table, `api_tokens`, holds every token. Each row has: `id`, `user_id`, `name`, `token_hash` (SHA-256 hex, unique index), `created_at`, `expires_at` (`created_at` + 90 days), `last_used_at` (null until first use) and `revoked_at` (null while not revoked). A token is **active** when `revoked_at` is null and `expires_at` is later than now. The plaintext token exists only in server memory during the create request and in the create response body. It is never written to the table or the logs.

```mermaid
sequenceDiagram
    autonumber
    actor U as User (browser, Settings page)
    participant S as App server
    participant DB as Postgres api_tokens
    participant C as API client (script or CI)

    Note over U,DB: 1. Create token (session cookie required)
    U->>S: POST /settings/tokens {name}
    S->>DB: BEGIN, lock user row, count active tokens, check name not used by an active token
    alt 10 active already, or name in use
        S->>DB: ROLLBACK (nothing stored)
        S-->>U: 409 "Revoke a token first" or "Name already in use"
    else allowed
        S->>S: generate pat_ + 32 secure random chars, compute SHA-256
        S->>DB: INSERT user_id, name, token_hash, created_at, expires_at = now + 90 days, then COMMIT
        S-->>U: 201 {id, name, token = plaintext}, Cache-Control no-store
        Note over U: Plaintext shown once with Copy button. Closing the dialog discards it.
    end

    Note over U,DB: 2. List tokens
    U->>S: GET /settings/tokens
    S->>DB: SELECT active rows WHERE user_id = session user
    DB-->>S: rows
    S-->>U: name, created_at, expires_at, last_used_at or "Never" (no hash, no plaintext)

    Note over C,DB: 3. API call with a token
    C->>S: GET /api/... with Authorization Bearer pat_...
    S->>S: SHA-256 of presented token
    S->>DB: SELECT row WHERE token_hash = hash
    alt no row, revoked_at set, or expires_at passed
        S-->>C: 401 generic body (identical for all three)
    else active
        S->>DB: UPDATE last_used_at = now WHERE id = row AND (last_used_at is null OR older than 1 hour)
        Note over S,DB: At most one write per token per hour. If this write fails, log it and continue.
        S->>S: handle request as the row's user_id
        S-->>C: 200 API response
    end

    Note over U,DB: 4. Revoke token
    U->>S: DELETE /settings/tokens/{id} (after confirm dialog)
    S->>DB: UPDATE revoked_at = now WHERE id AND user_id = session user AND revoked_at is null
    alt 0 rows updated (not theirs, or already revoked)
        S-->>U: 404
    else 1 row updated
        S-->>U: 204, token removed from list
    end
    Note over C,S: The next request with this token finds revoked_at set at step 3 and gets 401. No validity cache exists.
```

**Failure notes**

- **Lost create response.** If the 201 never reaches the browser, the row is already committed. It shows up in the list with last used "Never". The user revokes it and creates another token. There is no endpoint that returns a plaintext again.
- **Limit race.** The count, the name check and the insert run in one transaction that holds a lock on the user's row. Two concurrent creates therefore cannot push the user past 10 active tokens.
- **Expiry** needs no job. Rows past `expires_at` stop authenticating and drop out of the list, and they also stop counting toward the limit.
