```
PASSWORD RESET BY EMAILED LINK

Actors: [Web] client   [API] server   [PG] Postgres   [Q] email queue
        [W] email worker -> [Mail] third-party provider

Table (new): reset_tokens(id, user_id, token_hash UNIQUE, created_at,
                          expires_at = created_at + 30 min, consumed_at NULL)
Reused:      users(password_hash), sessions(user_id, ...)

=== 1. REQUEST FLOW:  POST /forgot-password {email} ===========================

[Web] --email--> [API]
                  |
                  |  BEGIN
                  |  SELECT user BY email FOR UPDATE         (serialises per account)
                  |
                  +-- no such user ------------------------------+
                  |                                              |
                  |  count reset_tokens for user                 |
                  |  WHERE created_at > now() - 1 hour           |
                  |                                              |
                  +-- count >= 3 --------------------------------+
                  |                                              |
                  |  count < 3:                                  |
                  |   raw = 32 random bytes                      |
                  |   UPDATE reset_tokens SET consumed_at = now()|
                  |     WHERE user_id = U AND consumed_at IS NULL|  <- kills old links
                  |   INSERT reset_tokens(user_id, sha256(raw),  |
                  |     created_at = now(), expires_at = now()+30m)
                  |  COMMIT                                      |
                  |   [PG] <- the only copy of the token is its hash
                  |  enqueue job {user, link with raw token} -> [Q]
                  |                                              |
                  v                                              v
        200 "If an account exists for that address,      (same 200, same text,
             we've sent a link."                          no row, no job)

[Q] -> [W] -> [Mail] -> user's inbox
          |
          +-- send fails: retry up to 3x with backoff
              then log + drop job (existing behaviour, nobody told)

=== 2. LINK-CLICK FLOW:  GET /reset?token=RAW ==================================

user clicks link --> [Web] --token--> [API]
                                       |
                                       | SELECT FROM reset_tokens
                                       |  WHERE token_hash = sha256(RAW)
                                       |    AND consumed_at IS NULL
                                       |    AND expires_at > now()      (read only,
                                       |                                 nothing burned)
                         valid --------+-------- invalid / expired / used / unknown
                           |                              |
                           v                              v
              "Choose a new password" page     "This link has expired,
              (form keeps token)                request a new one" page
                           |                    (links back to Forgot password)
                           | submit {token, new_password}
                           v
              POST /reset-password
                           |
          +----------------+------------------------------------------+
          | 1. length >= 12?          no  -> 422 "too short"          |
          | 2. on breached list?      yes -> 422 "choose another"     |
          |                           (link NOT burned; retry until   |
          |                            it expires)                    |
          +----------------+------------------------------------------+
                           | both pass
                           v
                  BEGIN
                   UPDATE reset_tokens SET consumed_at = now()
                    WHERE token_hash = sha256(RAW)
                      AND consumed_at IS NULL AND expires_at > now()
                    RETURNING user_id
                      |-- 0 rows (expired/used/superseded since page load)
                      |       ROLLBACK -> show "link has expired" page
                      v
                   UPDATE users SET password_hash = hash(new) WHERE id = user_id
                   DELETE FROM sessions WHERE user_id = user_id   (every device,
                  COMMIT                                           including this one)
                           |
                           v
              enqueue "your password was changed" -> [Q] -> [W] -> [Mail]
              302 redirect to /login        (no session is created)

=== 3. FAILURE PATHS ===========================================================

 Where                         What happens                                  Result
 ----------------------------  --------------------------------------------  ---------------------------
 Unknown email                 generic 200, nothing stored or sent           user cannot tell
 4th request within an hour    generic 200, no row, no job                   no new link; old link stays
 DB error on request           transaction rolls back, return 5xx to client  old link unchanged
 Enqueue fails after commit    log; still return generic 200                 link exists, nobody has it;
                                                                             user requests again
 Mail send fails 3x            worker drops job (existing)                   user gets no email and no
                                                                             notice; must request again
 Token invalid/expired/used    "link has expired" page (on load and submit)  user requests a new link
   on load or on submit
 Old link after a newer one    consumed_at set at issue time -> invalid      "link has expired" page
 Two submits race on one link  only one UPDATE ... RETURNING gets a row      loser sees "expired" page
 Password too short/breached   422, token untouched                          user retries
 Breached-list check down      fail closed: 503 "try again", token untouched  user retries
 DB error during reset commit  whole transaction rolls back                  password, sessions, link
                                                                             all unchanged
 "Password changed" mail fails reset already committed; email dropped        reset stands; no notice
```

**Notes**

- **Data kept.** One new table, `reset_tokens`. The raw token is never stored, only its SHA-256 hash. `consumed_at` covers both "used" and "replaced by a newer link", so one column and one check cover every dead link. Nothing else is needed.
- **Rate limit without a counter.** The rolling-hour limit counts `reset_tokens` rows created in the last hour. Every issued link is one row, and so is every email. Rows are never deleted at consume time. Any cleanup job must keep rows for at least an hour. The `FOR UPDATE` lock on the user row makes count-then-insert atomic, so concurrent requests can't exceed 3.
- **Same answer for every request.** Unknown, rate-limited and successful requests return the same body. Keep the work on the known-account path light (one transaction and an enqueue) so response timing doesn't give much away.
- **Check on load, check again on submit.** The page-load check only reads, so mail scanners that prefetch the link can't burn it. The submit check is the atomic `UPDATE ... WHERE consumed_at IS NULL AND expires_at > now() RETURNING`. It is the real gate, and it also settles races and links that expired while the form was open.
- **Rejected passwords don't burn the link.** Length and breach checks run before the consume step, so a rejected password never touches the token. Because consuming the token, setting the password and deleting sessions share one transaction, any failure leaves the old password, the live sessions and the usable link all intact.
- **Logout everywhere.** The API checks `sessions` on every request. Deleting all of the user's rows therefore logs out every device, including the resetting one, on its next request. The redirect goes to login with no new session.
- **Mail failures are silent (known gap).** The worker drops jobs after 3 failed retries and tells nobody, so a user whose reset email fails sees nothing. The design relies on the user requesting again, and the failed attempt still counts toward their 3 per hour. I did not change the worker. If this matters, the fix is to alert on dropped `reset` jobs. It is outside this feature's requirements.
- **Link hygiene.** Serve `/reset` with `Referrer-Policy: no-referrer` and no third-party scripts. Never log the raw token or full URL on the API, the queue job payload or the worker. The job has to carry the raw token to build the link, so it should be removed or redacted once the job finishes or is dropped.