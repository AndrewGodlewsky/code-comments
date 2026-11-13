# Password reset by emailed link

A user who forgot their password asks for a link by email. The link opens a page where they choose a new password. A successful reset ends all their sessions and sends them to the login page. Three flows follow: requesting a link, clicking it, and what happens when things fail.

## Terms

- **raw token**: 32 random bytes. It appears only in the emailed link (and briefly in the queued mail job). Only its SHA-256 hash is stored.
- **link**: `<APP_BASE_URL>/reset?token=RAW`. `APP_BASE_URL` is a config value of the web app.
- **live link**: a stored token row with `dead_at IS NULL AND expires_at > now()`.
- **dead**: `dead_at` is set when a link is used or replaced by a newer one. Dead rows are kept.

## Data

One new table. It reuses the existing `users`, `sessions` and email queue.

```
password_reset_tokens(token_hash PK, user_id FK, issued_at, expires_at = issued_at + 30m, dead_at NULL)
```

Rate limit: count the rows for the user with `issued_at > now() - 1h`. There is no separate counter. Used and replaced rows count too, because the limit is on reset emails sent per hour.

## Diagram

```
==================== 1. REQUEST FLOW  (POST /forgot-password {email}) ====================

 Web client            API server                                   Postgres        Email queue/worker
     | email                |                                          |                  |
     |--------------------->| find user by email (trim + lowercase) -->|                  |
     |                      |                                          |                  |
     |                      | no user ---------------------------------------> (send nothing)
     |                      |                                          |                  |
     |                      | user found:                              |                  |
     |                      |  1. BEGIN; SELECT user FOR UPDATE ------>|  (row lock: one  |
     |                      |  2. count rows from last 1h              |   request per    |
     |                      |  3. count >= 3 ? yes -> ROLLBACK ----------> (send nothing)  |
     |                      |  4. no: raw = 32 random bytes            |   user at a time)|
     |                      |  5. UPDATE tokens SET dead_at = now()    |                  |
     |                      |       WHERE user_id=? AND dead_at IS NULL>|  (kills old link)|
     |                      |  6. INSERT (sha256(raw), user_id,        |                  |
     |                      |       now, now+30m) -------------------->|                  |
     |                      |  7. COMMIT                               |                  |
     |                      |  8. enqueue {to: user's email,           |                  |
     |                      |       link with raw} ---------------------------------------->|--> mail provider
     |                      |                                          |                  |   (3 retries,
     |<-- 200 generic message (same status and body in every case) ----|                  |    then drop)
     |    "If an account exists for that address, we've sent a link."

 Paths that send nothing: unknown address | over 3/hour (no row, no job, old link untouched)


==================== 2. LINK-CLICK FLOW  (no login; the token is the credential) ====================

 GET /reset?token=RAW                                   (page load)
     |-> h = sha256(RAW); look for a live link with token_hash = h
     |      found      --> show "choose a new password" form (RAW in a hidden field)
     |      not found  --> show "this link has expired, request a new one" page
     |                     (unknown, expired, used and replaced all look the same)

 POST /reset {token: RAW, password}                     (form submit; token is in the body)
     |-> 1. Check the token is live (plain SELECT).
     |        not live --> "expired" page, even if the password is weak
     |-> 2. Validate the password: length >= 12 AND not on the breached list.
     |        fail --> re-show form with the reason. Nothing written; link stays live.
     |-> 3. BEGIN
     |        UPDATE tokens SET dead_at = now()
     |          WHERE token_hash = sha256(RAW) AND dead_at IS NULL AND expires_at > now()
     |          RETURNING user_id          (re-checks the token and burns it in one statement)
     |        0 rows --> ROLLBACK --> "expired" page
     |        1 row  --> UPDATE users SET password_hash = hash(password) WHERE id = user_id
     |                   DELETE FROM sessions WHERE user_id = user_id   (every device, incl. this one)
     |                   COMMIT
     |-> 4. Enqueue a "your password was changed" email to the account address.
     |-> 5. 302 redirect to /login. No session is created; the user logs in by hand.


==================== 3. FAILURE PATHS ====================

 Failure                               Result
 ------------------------------------  ---------------------------------------------------------
 Unknown email                         Generic message; no row, no email
 Over 3 links in the rolling hour      Generic message only (the fixed text cannot say "wait");
                                       no row, no email, existing link kept
 Enqueue fails after COMMIT (step 8)   Log it; generic message anyway. The old link is dead and
                                       the new one never goes out, so the user must request again
                                       (counts toward 3/hour; if at the limit, they wait until the
                                       earliest request is over an hour old)
 Mail send fails 3x (job dropped)      Link never arrives; the user gets no signal and must
                                       re-request (counts toward 3/hour)
 Link expired / used / replaced        "Expired" page at load and at submit
 Two submits race on one link          The conditional UPDATE lets one win; the other gets "expired"
 Password too short or breached        Form re-shown; link stays usable until it expires
 Breached-list lookup unavailable      Treat as rejected ("try again"); never accept unchecked
 DB error in submit step 3             Whole transaction rolls back: password, link and sessions
                                       unchanged. Show "something went wrong, please try again";
                                       the link is still live. The typed password is not kept.
 Step 4 enqueue fails, or server dies  The reset stands. The user is redirected to /login (or sees
   after COMMIT                        nothing if the server died); no notice email
```

## Notes

- **Locking.** The request flow holds a row lock on the user for the count, the kill and the insert. Parallel requests cannot slip past the limit of 3 or leave two live links.
- **Order on submit.** The token is checked first so a dead link never shows a password complaint. The password is validated before the burn, so a rejected password never uses up the link. The burn is one conditional UPDATE, so the final token check and "works once" are the same atomic step.
- **Logout.** The API checks `sessions` on every request. Deleting the user's rows in the same transaction as the password change logs out every device.
- **Cleanup.** Rows are kept after use so the same table gives the rate-limit count. A periodic delete (any scheduler, e.g. daily) removes rows with `issued_at` older than 1 day.
- **Silent mail loss.** The existing worker logs and drops a job after 3 failed sends and tells nobody. A dropped reset email still uses one of the 3 hourly sends and replaces the earlier link. The worker is not changed here, to keep scope small. A failure alert on the worker is a sensible follow-up.
- **Enumeration.** Responses are identical, and sending is queued rather than inline, so known and unknown addresses take similar time. The extra DB work for known accounts is small.
- **Link hygiene.** Send the reset page with `Referrer-Policy: no-referrer` and do not log the query string, so the raw token does not leak.

## Open questions

- Where the breached-password list lives and how it is queried (local file, table or service) is not specified; the flow needs only a yes/no answer.
- Assumes `users.email` is unique and compared after trim and lowercase. If the schema allows duplicates, the lookup rule needs deciding.
- Which scheduler runs the periodic row delete is not specified.
