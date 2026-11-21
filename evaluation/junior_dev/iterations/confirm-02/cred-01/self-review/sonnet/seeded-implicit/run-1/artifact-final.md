## Personal API tokens: design

Users create personal API tokens on the Account Settings page. Scripts and CI jobs send a token to the REST API instead of a password. One web/API server and one Postgres database handle everything.

There are two kinds of caller. Settings calls (create, list, revoke) come from the browser with a session cookie. API calls come from scripts with `Authorization: Bearer <token>`.

### Where state lives

| State | Location |
|---|---|
| Token record: id, user_id, name, SHA-256 hash, created_at, expires_at, revoked_at, last_used_at | New Postgres table `api_tokens`. The hash column has a unique index. |
| Plaintext token | Not stored anywhere. It exists only in the create response and the user's clipboard. It is never written to the database, logs or analytics. |
| Login session | Session cookie. It already exists and protects the settings endpoints. |
| Token validity | Not cached. Every API request reads the database, so a revoke takes effect on the next request. |

### Rules

- **Format.** `pat_` followed by 32 characters from a cryptographically secure random source.
- **Name.** 1 to 40 characters, unique among the user's active tokens.
- **Active.** Not revoked and not expired.
- **Expiry.** 90 days after creation. Tokens cannot be renewed.
- **Limit.** At most 10 active tokens per user.
- **Last used.** May be up to 1 hour out of date. The server writes it at most once an hour per token, so there is no database write on every request.
- **Ownership.** Users can list and revoke only their own tokens. Every settings query filters on the session's user_id.
- **Shown once.** The token appears only in the create response. After the user closes the create dialog, nobody can show it again, including support and engineering. A lost token means creating a new one.

### Diagram

```mermaid
sequenceDiagram
    actor User as User (browser)
    participant S as Server
    participant DB as Postgres (api_tokens)
    participant C as API client (script / CI)

    Note over User,DB: 1. Create token (session cookie required)
    User->>S: POST /settings/tokens {name}
    S->>S: Validate session and name (1-40 chars)
    alt Name is invalid or already used by an active token
        S-->>User: 400 / 409, nothing stored
    else Name is valid
        S->>DB: Count the user's active tokens
        alt Count is 10 or more
            S-->>User: 409 "Limit reached. Revoke a token first." Nothing stored.
            Note over S,DB: This is the normal path. Simultaneous creates are handled in the INSERT step below.
        else Count is under 10
            S->>S: Generate "pat_" + 32 random chars, compute SHA-256 hash
            S->>DB: INSERT user_id, name, hash, created_at, expires_at = created_at + 90 days
            Note right of DB: Only the hash is stored. A unique constraint on the<br/>user's active names, plus a re-check of the count inside<br/>the same transaction, stops two simultaneous creates<br/>from breaking the name or limit rules.
            S-->>User: 201 {full token, name, expiry} (the only time the plaintext is sent)
            Note over User: Dialog shows the token with a Copy button
        end
    end
    Note over User,S: Failure: the 201 never reaches the browser.<br/>The row exists but nobody has the token.<br/>The user sees the new name in the list, revokes it, and creates another.<br/>The server cannot re-send the token because it never stored it.

    Note over User,DB: 2. List tokens (session cookie required)
    User->>S: GET /settings/tokens
    S->>DB: SELECT name, created_at, expires_at, last_used_at<br/>WHERE user_id = session user AND revoked_at IS NULL AND expires_at > now()
    S-->>User: Active tokens only. The hash is never returned.<br/>A null last_used_at shows as "Never".

    Note over C,DB: 3. API call with a token
    C->>S: Request with Authorization: Bearer pat_...
    S->>S: Hash the presented token with SHA-256
    S->>DB: SELECT by hash WHERE revoked_at IS NULL AND expires_at > now()
    alt Header missing, token unknown, revoked or expired
        S-->>C: 401 with the same generic body in every case
    else Token is active
        opt last_used_at is null or older than 1 hour
            S->>DB: UPDATE last_used_at = now()
            Note right of DB: At most one write per token per hour.<br/>If this write fails, the request still succeeds.
        end
        S-->>C: Normal response, acting as the token's user
    end

    Note over User,DB: 4. Revoke token (session cookie required)
    User->>S: Click Revoke, confirm, then DELETE /settings/tokens/{id}
    S->>DB: UPDATE SET revoked_at = now()<br/>WHERE id = {id} AND user_id = session user
    alt No such token for this user
        S-->>User: 404 (same answer for another user's token)
    else Updated
        S-->>User: 204
    end
    Note over C,S: The next API request with this token reads the database,<br/>finds revoked_at set and gets 401. No cache means no delay.
```

### Failure summary

| Situation | Result |
|---|---|
| Limit reached on create | 409 with a message telling the user to revoke a token first. No row is written. |
| Invalid or duplicate name | 400 or 409. No row is written. |
| Bad token on an API call (missing, unknown, revoked or expired) | 401 with an identical generic body, so the response does not reveal which case it was. |
| Create response lost in transit | The token exists but its plaintext is gone. The user revokes it and creates a new one. |
| Revoke for a token that is not the user's | 404. |
| Last-used update fails | The request still succeeds. The displayed time is just more out of date. |