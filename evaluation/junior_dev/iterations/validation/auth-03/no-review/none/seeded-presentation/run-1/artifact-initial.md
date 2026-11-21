```
                  +------------------------------------------+
   user/browser   |  API (backend / server / "the app")      |
  +-----------+   |                                          |   +----------------------+
  |           |-->|  /password-reset   (*1)(*7)              |-->|  DB: users,          |
  |  client   |   |  /reset GET        (*3)                  |   |  sessions ("logins"),|
  |           |<--|  /reset POST       (*2)(*5)(*9)          |<--|  pw_reset table (*4) |
  +-----------+   +------------------------------------------+   +----------------------+
        ^                 |                     |
        |                 | (*6) job            | (*8) 2nd job
        |                 v                     v
        |          +--------------------------------+     +---------+     +-----------+
        |          |   queue (mail)                 |---->| sender  |---->| provider  |
        |          +--------------------------------+     +---------+     +-----------+
        |                                                    |   ^
        +------------------ inbox <--------------------------+   | (*10)
                                                             +---+
```

(*5) This is where the new password actually goes in. In one transaction, the reset record gets its used_at stamped, but only through an UPDATE with WHERE id = row AND used_at IS NULL AND expires_at > now(). If that touches 0 rows, because another submit of the same link got there first or the half hour ran out a moment ago, it ROLLBACKs and you get the expired page. Otherwise users.password_hash is updated and every row in sessions for that user is deleted, including the phone or laptop the person is resetting from, then COMMIT.

(*1) Forgot-password endpoint: the answer is always 200 "If an account exists for that address, we've sent a link.", whatever happened.

(*9) After that the browser is redirected to /login. No session is made for them; they sign in with the new password.

(*4) pw_reset table = id, user_id, token_hash (SHA-256 of the raw code), created_at, expires_at (which is created_at + 30 min), used_at (null means the link is live). The raw value is never stored in Postgres. It exists only in API memory during the request, in the queued job, in the email itself and in whatever URL or form field comes back from the browser, so a DB leak gives away hashes only.

(*10) Provider errors: the sender retries with backoff up to 3 more times, then logs and drops the job. Nobody is notified; the person can just ask again.

(*3) GET with ?token=<raw>: the API hashes it (SHA-256) and selects the reset record whose token_hash matches. The record must exist, have used_at null and an expires_at in the future, or you get the "This link has expired, request a new one" page; otherwise the choose-new-password form, with the token in a hidden input. Nothing is written at this point, so merely opening the link doesn't use it up. The record's user_id is how the API knows which account.

(*7) Inside the forgot endpoint: look the email up in users. If it isn't found, skip straight to the (*1) response with no write and no mail. If found, a transaction is opened and the first thing in it is SELECT id FROM users WHERE id = user FOR UPDATE, which locks that account's users row so a second request for the same account that comes in at the same time just waits until this one commits or rolls back, and only after the lock is held are this user's pw_reset rows with created_at in the last 60 min counted (dead ones too); at 3 or more it ROLLBACKs and it's again just the (*1) response, nothing written, nothing sent. Otherwise 32 random bytes are generated as the code (in API memory). Still in that same transaction, all of the user's still-live tokens get used_at = now(). That is how older links die: they're stamped, not deleted, which matters because the 60-minute count reads them, and that count is the only rate-limit state there is. Then the new row is inserted with the hash and expires_at = now + 30m, and COMMIT releases the lock, so a request that was waiting counts this new row too.

(*6) The job carries to, template=reset and the link https://app/reset?token=<raw>. It goes on the queue after the transaction in (*7) commits and before the (*1) response.

(*2) Before (*5), the token is checked again, same as (*3); a failure gives the expired page. Then the password policy: 12 chars minimum, not on the breached list. If it fails, the form comes back with the error and nothing is written, so the key keeps working until expires_at.

(*8) The "password changed" mail (template password-changed) is enqueued only after (*5) COMMITs. Same sender, same retry-then-drop.

Re the logins/sessions table: the API looks at it on every request, so deleting the rows logs every device out on its next call.
