# Personal API tokens: sequence diagram

The diagram covers four flows on the existing Account Settings page and the single web/API server: create, list, an API call that uses a token, and revoke. Token state lives in one new Postgres table, `api_tokens`. The server keeps no token state in memory, so it has no validity cache and no buffer of last-used times. The only places the plaintext token ever exists are the CSPRNG output on the server while the create request runs, the create response, the browser dialog while it is open, and wherever the user pastes it.

Settings endpoints (`/settings/tokens...`) accept only the session cookie. A bearer token cannot create, list or revoke tokens, so a leaked token cannot make new ones for itself.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant B as Browser<br/>Account Settings page
    participant C as API client<br/>(script or CI job)
    participant S as Web/API server<br/>(no token cache)
    participant DB as Postgres<br/>users, api_tokens
    participant L as Logs and analytics

    Note over DB: api_tokens: id, user_id (FK, cascade), name, token_hash (bytea, unique),<br/>created_at, expires_at, revoked_at (null), last_used_at (null)<br/>Active means revoked_at is null and expires_at is later than now()

    Note over U,L: Flow 1 - Create a token
    U->>B: Click Create token, type a name
    B->>B: Disable the Create button while the request is pending
    B->>S: POST /settings/tokens {name} with session cookie and CSRF token
    S->>S: Existing session check. Trim name, require 1 to 40 characters
    alt No valid session or bad CSRF token
        S-->>B: 401 or 403 (existing behaviour), nothing created
    else Name empty or over 40 characters
        S-->>B: 422 invalid_name
        B-->>U: "Name must be 1 to 40 characters."
    else Valid request
        S->>DB: BEGIN, then SELECT the user's row FOR UPDATE
        Note right of DB: The row lock serialises this user's creates, so two parallel<br/>requests cannot both pass the limit check or the name check
        S->>DB: Count active tokens, and find any active token with the same name
        alt Already 10 active tokens
            S->>DB: ROLLBACK
            S-->>B: 409 token_limit_reached
            B-->>U: "You have 10 active tokens. Revoke a token before creating a new one."
        else An active token already has this name
            S->>DB: ROLLBACK
            S-->>B: 409 name_taken
            B-->>U: "You already have an active token with this name. If you never saw it, revoke it and create it again."
        else Under the limit and the name is free
            S->>S: token = "pat_" + 32 chars [A-Za-z0-9] from the CSPRNG (rejection sampling)<br/>hash = SHA-256(token)
            S->>DB: INSERT (user_id, name, hash, created_at = now(), expires_at = now() + 90 days), then COMMIT
            Note right of DB: If the unique index on token_hash rejects the insert (practically never),<br/>generate a new token and retry
            S->>L: Event token_created {user_id, token_id}, never the token or its hash
            S-->>B: 201 {id, name, created_at, expires_at, token} with Cache-Control no-store
            Note over S: The request logger does not log this response body.<br/>The server keeps no copy once the response is sent
            alt Response arrives
                B-->>U: Dialog shows the token once, with a Copy button and "You will not see this again"
                U->>B: Copy, then close the dialog
                B->>B: Drop the token from page memory, reload the list (Flow 2)
            else Response never arrives (timeout, dropped connection, tab closed)
                Note over B,DB: The browser cannot tell whether the COMMIT happened. If it did, the token exists<br/>and counts toward the limit, but nobody holds the plaintext, and the server will not show it again
                B-->>U: "We could not confirm that the token was created."
                B->>S: GET /settings/tokens (Flow 2)
                alt A token with that name is in the list
                    B-->>U: "It was created but cannot be shown. Revoke it and create a new one."
                else Not in the list
                    B-->>U: "It was not created. Try again."
                end
            end
        end
    end

    Note over U,L: Flow 2 - List tokens
    B->>S: GET /settings/tokens with session cookie
    S->>DB: SELECT id, name, created_at, expires_at, last_used_at WHERE user_id = session user and the token is active, newest first
    DB-->>S: Rows (token_hash is never selected)
    S-->>B: 200 [{id, name, created_at, expires_at, last_used_at or null}]
    B-->>U: Table. A null last_used_at shows "Never". Each row has a Revoke button
    Note over B,DB: last_used_at can be up to 55 minutes behind the real last use (see Flow 3)

    Note over U,L: Flow 3 - API call authenticated by a token
    C->>S: GET /api/... with Authorization: Bearer pat_...
    S->>S: Check format: header present, scheme Bearer, "pat_" followed by exactly 32 allowed characters
    alt Header missing or malformed
        S->>L: auth_failed {reason: missing or malformed}, Authorization header redacted
        S-->>C: 401 {"error":"invalid_token"} with WWW-Authenticate: Bearer
    else Well formed
        S->>S: hash = SHA-256(token)
        S->>DB: SELECT id, user_id, is_active, needs_touch WHERE token_hash = hash
        Note right of DB: This reads the primary on every request. Postgres computes is_active and<br/>needs_touch (last_used_at null or older than 55 minutes) using its own clock.<br/>Nothing is cached, so revoke and expiry apply to the next request
        alt No row (unknown) or is_active false (revoked or expired)
            DB-->>S: No row, or the row with is_active false
            S->>L: auth_failed {reason, token_id if known}, never the token or its hash
            S-->>C: 401 {"error":"invalid_token"}, the same body and headers as above
        else Active row
            DB-->>S: id, user_id, is_active true, needs_touch
            opt needs_touch is true
                S->>DB: UPDATE api_tokens SET last_used_at = now() WHERE id = token id
                Note right of DB: At most one write per token per 55 minutes. If the write fails,<br/>log it and still serve the request. The next request tries again
            end
            S->>S: Run the API handler as user_id
            S-->>C: 2xx response
        end
    end

    Note over U,L: Flow 4 - Revoke a token
    U->>B: Click Revoke on a row
    B-->>U: Confirm "Revoke 'ci-deploy'? Anything using it stops working right away."
    alt User cancels
        B-->>U: Dialog closes, nothing sent
    else User confirms
        B->>S: DELETE /settings/tokens/{id} with session cookie and CSRF token
        S->>DB: UPDATE api_tokens SET revoked_at = COALESCE(revoked_at, now()) WHERE id = {id} AND user_id = session user, then COMMIT
        alt 0 rows (no such token, or it belongs to another user)
            S-->>B: 404, the same for both cases
            B-->>U: "Token not found." Reload the list
        else 1 row updated
            S->>L: Event token_revoked {user_id, token_id}
            S-->>B: 204
            B->>S: GET /settings/tokens (Flow 2), the row is gone
        else Response never arrives
            B-->>U: "Could not confirm." User retries, and repeating the revoke is safe
        end
    end
    C->>S: Next API request with the revoked token
    S->>DB: Look up by hash (Flow 3)
    DB-->>S: Row with is_active false
    S-->>C: 401 {"error":"invalid_token"}
```

## Where state lives

| State | Location | Notes |
|---|---|---|
| Token record (name, dates, revoked flag) | `api_tokens` row in Postgres | Unique index on `token_hash`, index on `user_id`. Revoked and expired rows stay for audit. They are inactive, so they drop out of the list and the limit without any cleanup job. |
| Token hash | `api_tokens.token_hash` | SHA-256 of the full string, including `pat_`. No salt is needed because the token carries about 190 bits of randomness. Never returned by any endpoint or logged. |
| Plaintext token | The server's memory while the create request runs, the 201 response, the browser dialog, and the client's secret store | Never written to Postgres, logs, analytics or error reports. The browser drops it when the dialog closes. |
| Expiry | `expires_at`, set once at insert | No endpoint can change it, so tokens cannot be renewed. |
| Last-used time | `api_tokens.last_used_at` | Written at most once every 55 minutes per token. Postgres decides, so there is no in-memory buffer to lose and the lag stays under 1 hour. |
| Session | Existing session cookie and session store | Used only by the settings endpoints. |

## Failure handling

- **Limit reached.** Creating an 11th token returns 409 `token_limit_reached` and the message "Revoke a token before creating a new one." The lock on the user's row stops two parallel creates both slipping past the count.
- **Duplicate name.** Returns 409 `name_taken`. Names are compared exactly, after trimming whitespace. A name used only by revoked or expired tokens is free again. A double-click on Create also ends here, so it never makes two tokens.
- **Bad token.** Missing, malformed, unknown, revoked and expired tokens all get the same 401 body and `WWW-Authenticate` header. The reason goes only to the internal logs, recorded by token id.
- **Create response lost.** The server cannot replay the token, because that would mean storing the plaintext. The page reloads the list and tells the user either to revoke the orphan or to try again. If the user just retries, `name_taken` stops a silent duplicate, and its message explains what to do.
- **Revoke response lost.** Revoke is idempotent because of `COALESCE`, so the user can retry safely.
- **Revoke timing.** A request that starts after the revoke commits gets 401. A request that had already passed the token check before the commit may still finish.
- **last_used_at write fails.** The API call still succeeds. The next call retries the write. The 1-hour bound breaks only if that write fails and the token is never used again.

## Logging and analytics rules

- The request logger and error reporter redact the `Authorization` header on every route and drop the body of the create response.
- Analytics events carry `user_id` and `token_id` only.
- Any session-replay or DOM-capture script on the settings page must mask the token dialog.
- The token never goes in a URL or query string.

## Open questions

- If the account is deleted, its tokens are deleted with it (FK cascade). Whether a disabled or locked account should also fail token checks is not covered by the brief. If it should, add the user's status to the Flow 3 lookup.
- If read replicas are added later, the token lookup in Flow 3 must stay on the primary, or revoke would no longer apply to the very next request.
