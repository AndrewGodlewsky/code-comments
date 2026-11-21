```
PASSWORD RESET BY EMAILED ONE-TIME LINK

STATE (Postgres unless noted)
  users          id, email, password_hash
  sessions       one row per logged-in device; API checks it on every request
  reset_tokens   id, user_id, token_hash = SHA-256(raw token),
                 created_at, expires_at = created_at + 30 min,
                 used_at (NULL = link still live)
  email queue    existing queue + worker; jobs are {to, template, link?}

  The raw token is never stored in Postgres. It exists only in API memory
  during the request, in the queued email job, in the email, and in the
  URL/form the browser sends back.


=== 1. REQUEST A LINK =====================================================

[Browser] POST /password-reset {email}
   |
   v
[API] find user by email in users
   |-- no such user --> go to RESPOND (write nothing, send nothing)
   v
[API -> Postgres] ONE TRANSACTION
      a. SELECT id FROM users WHERE id = <user> FOR UPDATE
         (locks this account; a parallel request for it waits here)
      b. count this user's reset_tokens rows with
           created_at > now() - 60 min   (live and dead rows both count)
         count >= 3 --> ROLLBACK --> go to RESPOND
                        (nothing written, nothing sent)
      c. raw token = 32 random bytes (API memory only)
      d. UPDATE reset_tokens SET used_at = now()
           WHERE user_id = <user> AND used_at IS NULL
         (every earlier unused link for this account dies here)
      e. INSERT {user_id, token_hash = SHA-256(raw),
                 created_at = now, expires_at = now + 30 min}
   COMMIT  (releases the lock; a waiting request now counts this row)
   |
   v
[API -> email queue] job {to: email, template: reset,
                          link: https://app/reset?token=<raw>}
   |
   v
RESPOND
[API -> Browser] 200 "If an account exists for that address, we've sent
                 a link."  Same status and text on all three paths.

   ... later, asynchronously ...

[Email worker] takes job, sends via mail provider
   |-- send fails --> retry with backoff, up to 3 retries
   |                    |-- still failing --> log error, drop job.
   |                        No one is told; the user requests again.
   v
[User inbox] email with the link


=== 2. OPEN THE LINK ======================================================

[Browser] GET /reset?token=<raw>
   |
   v
[API] row = reset_tokens WHERE token_hash = SHA-256(<raw>)
      OK only if row exists AND used_at IS NULL AND expires_at > now
      (row.user_id tells the API which account this is)
   |-- not OK --> "This link has expired, request a new one" page
   v
[API -> Browser] "Choose a new password" form, token in a hidden field.
                 Nothing is written; opening the link does not burn it.


=== 3. SUBMIT THE NEW PASSWORD ============================================

[Browser] POST /reset {token, new_password}
   |
   v
[API] re-check the token exactly as in step 2
   |-- not OK --> expired-link page
   v
[API] new_password >= 12 chars AND not on breached-password list?
   |-- no --> form again with the error. Nothing written; the same
   |          link keeps working until its expires_at.
   v
[API -> Postgres] ONE TRANSACTION
      a. UPDATE reset_tokens SET used_at = now()
           WHERE id = <row> AND used_at IS NULL AND expires_at > now()
         0 rows updated (a parallel submit won, or it just expired)
           --> ROLLBACK --> expired-link page
      b. UPDATE users SET password_hash = <hash of new_password>
      c. DELETE FROM sessions WHERE user_id = <user>
         (every device, including the one doing the reset)
   COMMIT
   |
   v
[API -> email queue] job {to: email, template: password-changed}
      Enqueued only after COMMIT; same worker, same retry-then-drop rule.
   |
   v
[API -> Browser] redirect to /login. No session is created; the user
                 logs in with the new password.
```

Notes
- Old links die by having `used_at` set, not by being deleted, so the hourly count in step 1 still sees them.
- The hourly limit needs no separate counter: it is the count of the account's `reset_tokens` rows from the last 60 minutes, so old requests age out on their own.
- The count runs inside the issuing transaction, after the account's `users` row is locked. Two requests for the same account that arrive together are therefore handled one after the other, and they cannot both get past a count of 2.
- Deleting the `sessions` rows logs every device out on its next request, because the API checks `sessions` on every call.
- A database leak exposes only hashes, which cannot be turned back into working links.
