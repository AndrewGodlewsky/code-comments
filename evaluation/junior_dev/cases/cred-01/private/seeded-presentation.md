Notes: so the PAT (key / credential / secret, all the same thing) is checked by the backend: it takes the SHA-256 of whatever comes in the Bearer header and looks it up by hash, which only works because we never keep the plaintext. The key only lives in memory while the create request runs and in the 201 body, which goes out with Cache-Control no-store and is never logged. If the credential row has revoked_at set, or expires_at (created_at plus 90 days) is in the past, or there's no row, the caller gets a 401, and it's the same generic body whichever it was. Also, on revoke we don't delete the row, we just stamp revoked_at, scoped to user_id and revoked_at null, so somebody else's id or an already-revoked one gives 404. Because there's no validity cache, the next call with that secret is a 401. Last used is touched hourly-ish, see the diagram, and the table has id, user_id, name, token_hash (unique), created_at, expires_at, last_used_at, revoked_at, and active means not revoked and not expired.

```mermaid
sequenceDiagram
    participant FE as settings pg
    participant srv as Server
    participant cli as caller
    participant pg as PG
    participant tbl as api_tokens (table inside PG)
    actor usr as user
    usr->>FE: clicks Revoke + confirms
    FE->>srv: DELETE /settings/tokens/{id}
    srv->>tbl: set revoked_at=now (id, user_id=session user, revoked_at null)
    tbl-->>srv: n rows
    srv-->>FE: 204 or 404 if n=0
    Note right of tbl: soft delete, row stays, list query filters to active only
    cli->>srv: Bearer pat_...
    srv->>srv: sha256
    srv->>pg: by hash
    pg->>tbl: lookup
    tbl-->>srv: row?
    Note over srv: none or revoked or expired = 401 same body. ok = serve as row owner
    srv->>tbl: last_used_at=now only if null or older than 1h
    Note left of cli: last-used write failing is just logged, request goes on anyway. so List can be up to 1h stale
    srv-->>cli: 200 or 401
    usr->>FE: new key, name
    FE->>srv: POST /settings/tokens {name} w/ session cookie
    srv->>pg: BEGIN, lock user row, count active, check name
    Note over srv,pg: 10 or more active, or name already used by an active one, gives 409 Revoke a token first / Name in use, rollback, no insert
    srv->>srv: pat_ + 32 crypto-random chars, hash it
    srv->>tbl: insert user_id, name, hash, created_at, expires_at
    srv->>pg: COMMIT
    srv-->>FE: 201 {id, name, token} no-store
    FE-->>usr: show once + copy, gone when dialog closes
    Note over FE,usr: if the 201 is lost the secret is gone but the row is committed, it lists as Never used, revoke it and make a new one
    FE->>srv: GET /settings/tokens
    srv->>tbl: active for session user
    srv-->>FE: name, created, expires, last used or Never (no hash/plaintext)
```

Expired ones need no cleanup job: they stop authing, vanish from the list and don't count toward the 10, and the lock on the user row is what stops two parallel creates from going over.
