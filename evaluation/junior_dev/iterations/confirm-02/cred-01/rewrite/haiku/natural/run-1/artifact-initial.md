# Personal API tokens on Account Settings: sequence plan

Four flows on the existing Account Settings page, served by the web/API server and its Postgres database. The full token is returned once, in the create response, and only its SHA-256 hash is stored. Session-cookie auth already protects the settings endpoints. Token auth is added only for API calls.

## Where state lives

- **Plaintext token.** Generated in server memory and sent once in the 201 body. The browser holds it only in the dialog's memory. Closing the dialog discards it. It is never written to the database, logs or analytics.
- **`api_tokens` row (Postgres).** `id`, `user_id`, `name` (1 to 40 characters), `token_hash` (unique), `idempotency_key` (unique per user), `created_at`, `expires_at` (`created_at` + 90 days, fixed), `revoked_at` (nullable), `last_used_at` (nullable).
- **Last-used buffer (API server memory).** Maps token id to the latest time it was seen. It is flushed to Postgres every 5 minutes. A crash loses at most about 5 minutes of last-used data, which is inside the 1-hour allowance.
- **Logs and analytics.** Token id, user id and an outcome code only. The `Authorization` header and the create response body are redacted.
- **Validity cache.** None. Each API call reads `revoked_at` and `expires_at` from Postgres by hash, so revocation applies to the next request.

## Sequence diagram

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    actor C as API client (script or CI)
    participant UI as Account Settings page (browser)
    participant API as Web/API server
    participant BUF as Last-used buffer (API server memory)
    participant DB as Postgres api_tokens

    Note over U,DB: Flow 1: Create a token
    U->>UI: Enter name and click Create
    UI->>API: POST /settings/tokens with name and Idempotency-Key (session cookie and CSRF token)
    API->>API: Trim name and check 1 to 40 characters
    API->>DB: BEGIN and lock the user row
    API->>DB: Count active tokens and check name against active tokens
    alt Already 10 active tokens
        API-->>UI: 409 limit reached
        UI-->>U: Revoke a token first
    else Name already used by an active token
        API-->>UI: 422 name in use
        UI-->>U: Name error
    else Under limit and name free
        API->>API: Generate pat_ plus 32 characters from CSPRNG
        API->>API: token_hash = SHA-256 of the token
        API->>DB: INSERT row with token_hash and expires_at = now plus 90 days
        DB-->>API: COMMIT
        API-->>UI: 201 with token shown once (Cache-Control no-store)
        UI-->>U: Dialog with token and Copy button
        Note over UI: Token held in dialog memory only.<br/>Closing the dialog discards it.
    end
    opt Create response lost before the browser received it
        API-xUI: 201 never arrives
        Note over API,DB: Row exists, but nobody holds the plaintext and the server cannot resend it
        UI->>API: Retry with same Idempotency-Key
        API->>DB: Find row by user and Idempotency-Key
        API-->>UI: 409 token already issued and cannot be shown again
        UI-->>U: Revoke the stranded token and create a new one
    end

    Note over U,DB: Flow 2: List tokens
    U->>UI: Open Account Settings
    UI->>API: GET /settings/tokens (session cookie)
    API->>DB: SELECT name, created_at, expires_at, last_used_at for this user where not revoked and not expired
    DB-->>API: Active rows
    API-->>UI: 200 list (null last_used_at shows Never)
    UI-->>U: Table of active tokens
    Note over BUF,DB: last_used_at can trail real use by about 5 minutes plus flush, inside the 1-hour allowance

    Note over U,DB: Flow 3: API call authenticated by a token
    C->>API: Request with Authorization: Bearer pat_...
    API->>API: Parse header and compute SHA-256 of presented token
    API->>DB: SELECT user_id, revoked_at, expires_at WHERE token_hash = hash
    DB-->>API: Row or no row
    alt No row, revoked, or expired
        API-->>C: 401 generic body and WWW-Authenticate: Bearer
    else Valid row
        API->>BUF: Record token id and current time (memory only, no DB write)
        API-->>C: 200 with response for the token owner
    end
    loop Every 5 minutes on the API server
        BUF->>DB: One batch UPDATE of last_used_at using GREATEST, one row per token
        alt DB write fails
            BUF->>BUF: Keep entries and retry next cycle
        end
    end
    Note over API,DB: A DB read failure returns 503, not 401, so an outage is not read as bad tokens

    Note over U,DB: Flow 4: Revoke a token
    U->>UI: Click Revoke
    UI-->>U: Confirmation dialog
    U->>UI: Confirm
    UI->>API: POST /settings/tokens/:id/revoke (session cookie and CSRF token)
    API->>DB: SELECT owner of token id
    alt Token missing or owned by another user
        API-->>UI: 404
        UI-->>U: Token not found
    else Owned by this user
        API->>DB: UPDATE revoked_at = now WHERE id, owner and revoked_at is null
        DB-->>API: OK
        API-->>UI: 200 revoked (also 200 if this user already revoked it)
        UI-->>U: Token removed from list
    end
    C->>API: Next request with the revoked token
    API->>DB: SELECT by token_hash
    DB-->>API: Row with revoked_at set
    API-->>C: 401 generic body, same as any bad token
    Note over API,BUF: No cache holds validity, so the rejection takes effect on the next request
```

## Failure notes

- **Limit reached.** The count and the insert run in one transaction under a per-user row lock (`SELECT ... FOR UPDATE` on the user row). Two parallel creates cannot both take the 10th slot. The message reads: "You already have 10 active tokens. Revoke one before creating another."
- **Name uniqueness.** A plain unique index cannot express "active" because expiry depends on the current time, and index predicates cannot call `now()`. Enforce it in the same locked transaction, comparing trimmed names.
- **Lost create response.** The server cannot resend the plaintext, so the row exists with no holder. A retry with the same `Idempotency-Key` returns 409 and no token. The row counts toward the limit and shows as Never used until revoked or until it expires after 90 days. Recommended fix: the browser calls `POST /settings/tokens/:id/ack` when the dialog closes, and a sweep revokes any token not acked within 15 minutes. Acking is safe because an unacked token either was never delivered or was delivered and then abandoned.
- **Bad, unknown, revoked or expired token.** All return the same 401 body (`{"error":"unauthorized"}`) with the same headers, after the same hash-and-lookup path, so the response does not reveal which case applied.
- **Revoke.** A token not owned by the caller returns 404, the same as a missing token. Repeating a revoke for a token this user already revoked returns 200, so retries are safe.
- **Expiry.** There is no renew endpoint. Expired rows stay for history but are excluded from the list and from auth.
- **Browser safety.** Create and revoke are protected by a CSRF token on top of the session cookie. Create responses use `Cache-Control: no-store`.

## Open decisions

- Accept stranded tokens after a lost response, or add the ack and 15-minute sweep above.
- Whether name uniqueness is case-insensitive. Recommended: yes.
- Confirm the 10-token limit counts only active tokens, as the brief states.