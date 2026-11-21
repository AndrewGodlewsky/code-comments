# Personal API tokens on the Account Settings page

Signed-in users can create personal API tokens. A script or CI job (an automated process that runs without a person at the keyboard) then calls our REST API by sending the token in an HTTP header. It never needs the user's password.

Everything happens on the existing Account Settings page. Two parts of the system are involved:

- the **web/API server**, which handles every request from the browser and from API clients, and
- a **Postgres database** (a relational database), with a table named `api_tokens` that holds one row per token.

## Rules

- A token name is 1 to 40 characters. Each user's active tokens must have different names.
- A user may have at most 10 active tokens. The 11th create is refused.
- The full token is shown exactly once, right after it is created. It cannot be shown again, by the server, by support or by engineering. A user who loses a token creates a new one.
- A user can list and revoke only their own tokens.

## Key terms

- **Token**: a secret string made of the prefix `pat_` followed by 32 random characters. The server generates it with a cryptographically secure random source, so it cannot be guessed.
- **Hash**: the result of running the token through SHA-256, a standard one-way function. The same token always gives the same hash, but the hash cannot be turned back into the token. The database stores only the hash. If the database leaks, the attacker gets hashes, not usable tokens.
- **Active**: a token that has not been revoked and has not reached its expiry time.
- **Expiry**: every token expires 90 days after it is created. It cannot be extended. A user who needs more time creates a new token.
- **Last used**: the time the token was last accepted on an API call. It may be up to 1 hour out of date. The server writes it at most about once an hour per token. This keeps database writes rare, because the database is not written on every API request.
- **Row lock**: a database lock on the user's row. While one create request holds the lock, other create requests for the same user wait their turn.
- **Bearer header**: the standard way a client sends a token: `Authorization: Bearer <token>`.
- **Session cookie**: the browser's proof that the user is signed in. The settings pages use it. API clients do not.

## Where state lives

- **Browser**: holds the new token only while the one-time dialog is open. It is never saved.
- **Server**: keeps no state between requests. On every API call it checks the database, and it does not cache token validity. This means a revoke takes effect on the very next request.
- **Postgres (`api_tokens`)**: one row per token. Each row holds the user, the name, the token hash, the created time, the expiry time (created time plus 90 days), the revoked time (empty until the token is revoked) and the last-used time (empty until first use). The plaintext token is never stored.
- **Logs and analytics**: never contain the token value.

## Flows

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Server
    participant DB as Postgres api_tokens
    participant Client as API client

    Note over Server,DB: Create: the server generates the token and stores only its SHA-256 hash
    User->>Browser: enters a name of 1 to 40 characters and clicks Create
    Browser->>Server: POST /tokens with name (session cookie)
    Server->>Server: check name length, then generate pat_ plus 32 random characters
    Server->>DB: start transaction and lock this user's row, so creates run one at a time
    Server->>DB: count active tokens and check whether the name is used by an active token
    alt user already has 10 active tokens
        Server->>DB: roll back
        Server-->>Browser: 4xx, message says to revoke a token first
    else name already used by an active token
        Server->>DB: roll back
        Server-->>Browser: 4xx, name already in use
    else checks pass
        Server->>DB: insert row with SHA-256 hash and expires_at = now plus 90 days
        DB-->>Server: commit
        Server-->>Browser: 201 with the full token, shown once
        Browser-->>User: dialog shows the token with a Copy button, then closes for good
    end
    Note over Server,Browser: If the 201 never reaches the browser, the row still exists. The user never sees the token and must create a new one. The lost row still counts toward the limit until it is revoked or expires.

    Note over Browser,DB: List: the token value is never returned
    User->>Browser: opens Account Settings
    Browser->>Server: GET /tokens (session cookie)
    Server->>DB: select name, created, expiry and last-used for this user where not revoked and not expired
    DB-->>Server: matching rows
    Server-->>Browser: list, where last-used shows as Never if it is empty

    Note over Client,DB: API call: checked on every request with no cache, so revocation applies at once
    Client->>Server: API request with header Authorization: Bearer pat_...
    Note over Server: A missing or malformed header gets the same 401 as a bad token
    Server->>Server: compute SHA-256 of the presented token
    Server->>DB: select row by hash
    alt no row, revoked, or expired
        Server-->>Client: 401 with generic body
    else valid
        opt last-used is empty or more than 1 hour old
            Server->>DB: set last-used to now
        end
        Server-->>Client: normal API response
    end

    Note over User,DB: Revoke: the change applies to the next request
    User->>Browser: clicks Revoke and confirms
    Browser->>Server: POST /tokens/id/revoke (session cookie)
    Server->>DB: set revoked time where id matches and user is this user
    alt token not found or belongs to another user
        Server-->>Browser: 404
    else revoked
        Server-->>Browser: 200 ok
    end
    Client->>Server: next request with the revoked token
    Server-->>Client: 401 with generic body
```

## Failure cases

- **Limit reached**: the 11th create is refused with a 4xx error, and the message tells the user to revoke a token first. The row lock makes the count and the insert happen one create at a time. Without the lock, two simultaneous creates could both read a count of 9 and both insert, which would go over the limit.
- **Duplicate name**: refused with a 4xx error if the name matches another active token of the same user.
- **Bad token**: a missing, unknown, revoked or expired token all get the same 401 body. The response does not reveal which case applied.
- **Create response lost**: the row is saved, but the user never sees the token and cannot get it back. The user creates a new token. The lost row still counts toward the 10-token limit until it is revoked or expires, so the user may need to revoke it from the list.
- **Other users' tokens**: a user can list and revoke only their own tokens. An attempt to revoke someone else's token returns 404, the same as for a token that does not exist.