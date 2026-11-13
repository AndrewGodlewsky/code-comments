# Password reset by emailed link: design

## Diagram

```
 A. REQUEST FLOW: POST /password-reset {email}

   Client --> API server
               1. Look up the user by normalised email. No user: go to step 6.
               2. BEGIN; SELECT users WHERE id = $1 FOR UPDATE
                    (serialises concurrent requests for one account)
               3. Count reset_sends with sent_at > now() - 1h
                    count >= 3: ROLLBACK, go to step 6
               4. INSERT reset_sends (user_id, sent_at = now())
                  Enqueue job { user_id, send_id }   (no token in the job)
               5. COMMIT
               6. Respond 200 with the generic message. Same body and
                  same minimum response time on every path.
                                |
                                v
                  Email queue ---------> Email worker
                                         a. token = 32 random bytes
                                            hash  = SHA-256(token)
                                         b. Upsert password_reset_tokens
                                            keyed by user_id:
                                            set token_hash, expires_at =
                                            now() + 30m, used_at = NULL
                                            (previous link dies here)
                                         c. Send mail containing
                                            https://<app>/reset?t=<token>
                                         d. On send failure: retry up to 3
                                            times with backoff, then log and
                                            drop the job

 B. LINK CLICK: GET /reset?t=<token>

   Browser --> API server: hash = SHA-256(t)
                 SELECT FROM password_reset_tokens
                   WHERE token_hash = hash
                     AND used_at IS NULL
                     AND expires_at > now()
                 |-- no row --> "This link has expired, request a new one" page
                 '-- row     --> "Choose a new password" form
                                 (token carried in a hidden field)

 C. SUBMIT: POST /reset {t, password}

   Browser --> API server
                 1. hash = SHA-256(t). Check the row is still valid.
                    Not valid: expired page.
                 2. Check password >= 12 chars and not on breached list.
                    Rejected: re-render form. Token NOT consumed.
                 3. BEGIN
                 4. UPDATE password_reset_tokens SET used_at = now()
                      WHERE token_hash = hash AND used_at IS NULL
                        AND expires_at > now()
                      RETURNING user_id
                    0 rows: ROLLBACK, expired page.
                 5. UPDATE users SET password_hash = argon2id(password)
                      WHERE id = user_id
                 6. DELETE FROM sessions WHERE user_id = user_id
                      (every device, including this one)
                 7. INSERT outbox job "password changed" (same transaction)
                 8. COMMIT
                 9. 303 redirect to /login. No session cookie is set.
```

## Data

- **password_reset_tokens**: `user_id` (PK, FK to users), `token_hash` (unique, 32 bytes), `expires_at`, `used_at` (nullable). One row per account, so issuing a link overwrites the previous one. Purge rows older than expiry plus 24 hours.
- **reset_sends**: `id`, `user_id`, `sent_at`, with an index on `(user_id, sent_at)`. It backs the rolling-hour limit. Purge rows older than one hour.
- **Raw tokens are stored nowhere**, including queue payloads. Job payloads carry only `user_id` and `send_id`.
- `users` changes only in `password_hash`. `sessions` loses the user's rows.

## Notes

- **The worker mints the token.** The queue persists job payloads, so putting the link in a job would store the raw token and break the hash-only rule. The API therefore only records the send and enqueues it. Trade-off: a previous link stays valid until the worker mints the new one, which is normally seconds but longer if the queue is backed up.
- **The limit counts at enqueue time.** A send that later fails still uses one of the three slots. This keeps the limit effective against queue flooding. A user whose send was dropped may have to wait up to an hour.
- **Single-use is enforced by one atomic UPDATE** in step C.4. Two concurrent submissions cannot both win.
- **Password validation runs before the token is burned.** This is what keeps the link usable after a rejected password.
- **The breached-password check uses a local list.** No network call is made and the password is never sent to a third party.
- **Enumeration resistance** depends on identical body and timing. Pad the response to a fixed minimum latency so the known-account path and the unknown-account path look the same.

## Failure paths

1. **Unknown address.** No row, no job, same generic message.
2. **Over the hourly limit.** No `reset_sends` row and no token change. The existing link stays valid. Same generic message.
3. **Email send fails** (provider error or worker crash). Retried 3 times, then dropped and logged. Nobody is told. The token row stays active until expiry, but the user never received the link, so this is harmless. The user can request again, which counts against the limit. **Residual risk:** the user was told "we've sent a link" and got nothing. Mitigation: alert on dropped reset jobs and give support a runbook.
4. **Worker crashes after minting, before sending.** Same as 3. The new token overwrote the old one, so nothing stale is left live.
5. **Link opened after 30 minutes, after use, or after a newer link was issued.** Expired page on GET, and expired page on POST (step C.4 returns 0 rows).
6. **Double submit or two tabs.** The second submission hits 0 rows and gets the expired page. The first submission's password is the one that takes effect.
7. **Weak or breached password.** Form re-rendered with an error. The token is not consumed, so the user can retry until expiry.
8. **Database error during reset.** Everything in steps C.3 to C.8 is one transaction. It rolls back, so the password does not change and the token is not burned.
9. **"Password changed" email dropped.** The reset has already committed, and the outbox row makes the enqueue atomic with it. Retries are handled by the queue. If the job is dropped, alert on it as in 3.
10. **Another device still logged in.** Its session row is deleted, and the API checks sessions on every request, so that device is logged out on its next request.
11. **Token leakage through the URL** (Referer header, access logs). Set `Referrer-Policy: no-referrer` on reset pages, keep query strings out of access logs, and rely on single-use and the 30-minute window.

## Open decisions

- Confirm the queue is Postgres-backed so the outbox row can share a transaction. If not, enqueue after COMMIT and accept an at-least-once risk on the "password changed" email.
- Choose the breached-password source: a local list, which is recommended, or the k-anonymity range API.
- Consider a per-IP limit on the request endpoint. The spec does not require one.
