```
SYSTEM
 Browser --> API server --> Postgres
                |             users         (existing; includes password hash)
                |             sessions      (existing; one row per logged-in device;
                |                            checked on every API request)
                |             reset_tokens  (NEW, defined below)
                |
                +--> Email queue --> Email worker --> Mail provider

NEW TABLE  reset_tokens
 id, user_id, token_hash (SHA-256, unique), created_at, expires_at, used_at
 used_at NULL = link still usable.
 used_at is set when the link is used OR replaced by a newer link.

1. REQUEST A LINK    POST /forgot-password {email}
 API looks up the user by email
   |
   +-- no such user ------------------------------------> send nothing --+
   |                                                                      |
   +-- user found                                                         |
         One DB transaction. The user row is locked so that parallel      |
         requests cannot both pass the limit check.                       |
           count this user's reset_tokens where created_at > now - 1h     |
           |                                                              |
           +-- count >= 3 --------> create nothing, send nothing ---------+
           |                                                              |
           +-- count < 3                                                  |
                 set used_at = now on the user's unused tokens            |
                 token = 32 random bytes                                  |
                 insert row (hash(token), expires_at = now + 30 min)      |
               After commit: add queue job "reset email" containing       |
               the link https://<app>/reset?token=<token>                 |
                                                   |                      |
                                                   v                      v
   Every path responds with the same message:
   "If an account exists for that address, we've sent a link."

2. OPEN THE LINK     GET /reset?token=...
 Hash the token and look up the reset_tokens row by token_hash.
   +-- row missing, OR used_at set, OR expires_at <= now
   |       --> page: "this link has expired, request a new one"
   +-- otherwise --> page: "choose a new password"
                     (the form sends the token back on submit)

3. SET THE PASSWORD  POST /reset {token, new_password}
 a. Re-check the token as in step 2.
      If invalid --> "expired" page.
 b. Check the password: >= 12 characters AND not on the breached list.
      +-- rejected --> redisplay the form with the reason.
      |                Token untouched, so the user can retry until it expires.
 c. One DB transaction:
      UPDATE reset_tokens SET used_at = now
        WHERE token_hash = ? AND used_at IS NULL AND expires_at > now
      +-- 0 rows updated (another request won the race, or it just expired)
      |        --> roll back; "expired" page
      +-- 1 row updated
             update users.password_hash for that user
             delete ALL of that user's sessions rows
               (every device, including the one doing the reset)
 d. After commit: queue a "your password was changed" email,
    then redirect to the login page. The user is NOT logged in automatically.

EMAIL SEND FAILURES (apply to both emails): the worker retries up to 3 times
with backoff, then logs the failure and drops the job. Nobody is notified.
```

Notes
- Rate limit: no separate counter is needed. Every reset email sent has exactly one reset_tokens row, so counting rows created in the last hour gives the limit. Replaced and used links still count.
- Raw token: it exists only in the emailed link (and briefly in the queue job that carries it). The database holds only its hash.
- One live link: replacing earlier links happens in the same transaction as the insert, so at most one link per account is ever usable.
- Step 3c is the real guard. The earlier token checks only produce friendly errors. The conditional UPDATE keeps "works once" true even if two submissions race. Because the password change and session deletion share its transaction, a failure cannot leave a burned link with an unchanged password.
- Logout: sessions are checked on every request, so deleting the rows logs out every device immediately.
- Failed reset email: the user sees nothing wrong, and the attempt still counts toward the 3-per-hour limit. They see the generic message and can request again, up to the limit. Accepted for now. Alerting on dropped jobs would be a separate change to the worker.
- Failed "password changed" email: the reset is unaffected. The owner just is not warned.
- Breached-password check unavailable: reject with a "try again" message and keep the link usable. Do not skip the check.
- Timing: unknown addresses should respond about as fast as known ones. Sending is queued, so the API does no slow work on either path.