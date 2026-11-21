# Sign in with Google: flow and state plan

Google sign-in (OpenID Connect, authorization-code flow with PKCE, `state`, `nonce`, scopes `openid email profile`) sits beside email and password. Both entry points, every callback outcome and the password-confirmation loop are in the diagram. Every successful Google sign-in calls the existing `start_session(user_id)`, so the result is the same session as a password login. Google access and refresh tokens are never stored.

## Flowchart

```mermaid
flowchart TD
    L0(["Login page: Sign in with Google"]) --> L1["Create attempt in Redis: state, nonce, PKCE verifier, origin=login, next. TTL 600 s. Set state cookie"]
    S0(["Account Settings: Link Google"]) --> S1{"Valid session?"}
    S1 -->|"no"| S1x["Redirect to login page. Nothing changes"]
    S1 -->|"yes"| S2["Create attempt in Redis as above, plus user_id from session, origin=settings. Set state cookie"]
    L1 --> R["Redirect browser to Google authorize URL: openid email profile, PKCE S256, state, nonce"]
    S2 --> R
    R --> CB(["Browser returns to callback URL"])
    CB --> K1{"Query state equals cookie, and attempt exists in Redis?"}
    K1 -->|"no: unknown, expired, used, or mismatch"| E1["Error page. Nothing changes"]
    K1 -->|"yes"| K2["GETDEL attempt in Redis. Attempt is now spent"]
    K2 --> K3{"Google returned an error param?"}
    K3 -->|"yes, e.g. user pressed Cancel"| N1["Redirect to origin with neutral message. Nothing changes"]
    K3 -->|"no, code present"| K4["Server POST to Google token endpoint with code and code_verifier"]
    K4 -->|"network error, timeout, or non-200"| N2["Redirect to origin with neutral try again message. Nothing changes. Code not retried"]
    K4 -->|"200"| K5{"ID token valid: signature, iss, aud, exp, nonce"}
    K5 -->|"no"| E2["Error page. Nothing changes"]
    K5 -->|"yes"| K6["Read only sub, email, email_verified. Discard Google tokens"]
    K6 --> K7{"Origin?"}

    K7 -->|"settings"| T1{"Session still valid and user_id equals attempt user_id?"}
    T1 -->|"no"| N3["Redirect to login with neutral message. Nothing changes"]
    T1 -->|"yes"| T2{"sub already linked?"}
    T2 -->|"to this user"| T3["Redirect to settings: already linked. Nothing changes"]
    T2 -->|"to another user"| T4["Redirect to settings: refused, account in use. Nothing changes"]
    T2 -->|"no"| T5{"This user already has another Google account?"}
    T5 -->|"yes"| T6["Redirect to settings: unlink current Google first. Nothing changes"]
    T5 -->|"no"| T7{"email_verified true?"}
    T7 -->|"no"| T8["Redirect to settings: verify email first. Nothing changes"]
    T7 -->|"yes"| T9["INSERT google_identities (sub, user_id). Email match not required"]
    T9 -->|"unique violation"| T10["Refuse as in T4 or T6. Nothing changes"]
    T9 -->|"ok"| T11["Redirect to settings: Google linked. No new session"]

    K7 -->|"login"| G1{"sub in google_identities?"}
    G1 -->|"yes"| SI
    G1 -->|"no"| G2{"email_verified true?"}
    G2 -->|"no"| G2x["Refuse: sign in with email and password instead. Nothing created"]
    G2 -->|"yes"| G3{"Lowercased email matches a users row?"}
    G3 -->|"no"| G4["One transaction: INSERT users with password_hash NULL and email_verified_at now, then INSERT google_identities"]
    G4 -->|"unique violation on email (race)"| G3
    G4 -->|"ok"| SI
    G3 -->|"yes, user U"| G5{"U already has a Google account?"}
    G5 -->|"yes, a different one"| G5x["Refuse: account already has a different Google account. Nothing changes"]
    G5 -->|"no"| P0["Create pending link in Redis: pending_id to sub, U, origin, next. TTL 600 s. Set pending cookie"]
    P0 --> P1["Show password form for account U. No session yet"]
    P1 --> P2{"Pending record present and cookie matches?"}
    P2 -->|"no: expired or missing"| P2x["Page: confirmation expired, start again. Nothing changes"]
    P2 -->|"yes"| P3{"U locked_until in the future?"}
    P3 -->|"yes"| P4["Reject: Account temporarily locked. Password not checked. DELETE pending. Link discarded"]
    P3 -->|"no"| P5{"bcrypt password matches? NULL hash counts as no match"}
    P5 -->|"no"| P6["failed_logins + 1"]
    P6 --> P7{"failed_logins reached 5?"}
    P7 -->|"yes"| P8["Set locked_until to now + 15 min and failed_logins to 0. DELETE pending. Show locked message"]
    P7 -->|"no"| P9["Show wrong password message. Pending kept until its TTL"]
    P9 --> P1
    P5 -->|"yes"| P10["One transaction: failed_logins to 0, INSERT google_identities (sub, U)"]
    P10 -->|"unique violation (linked meanwhile)"| P11["DELETE pending. Refuse: link conflict. Nothing linked"]
    P10 -->|"ok"| P12["DELETE pending. Link is now permanent"]
    P12 --> SI
    SI["start_session(user_id): delete old sid row if any, INSERT sessions row, set sid cookie, clear oidc and pending cookies, redirect to next if relative else /home"]
```

## Notes on the flow

- **Start (both entry points).** Generate `state`, `nonce` and a PKCE `code_verifier` from random bytes. Store them in Redis under the state, with `origin`, `next` (login only) and `user_id` (settings only). Set the TTL to 600 s, which is the round-trip limit. The state is also set in a cookie so the callback can bind it to the browser that started the attempt. Settings start requires a valid session.
- **Callback is honoured once.** `GETDEL` makes the attempt single-use and atomic, so two concurrent callbacks cannot both proceed. Unknown, expired and already-used states all look the same and produce an error page with no state change.
- **Google error.** The attempt is validated and spent first, then the user returns to the origin page with a neutral message.
- **Failed code exchange.** The attempt is already spent. Nothing is created or changed. The user restarts from the origin page. The code is never retried, because authorization codes are single-use.
- **Linked sub.** Sign-in uses the linked user. Google email and `email_verified` are ignored, so an email change at Google still reaches the same account.
- **Unlinked, verified, no match.** The new user is created in one transaction with the link. If a concurrent signup takes the email, the flow re-runs the match and goes to the password branch.
- **Unlinked, verified, matched.** The link is not created here. A short-lived pending link is created, and the password form asks for that account's password. The only way to get the confirm step is a verified Google email, so the form does not reveal accounts to strangers.
- **Password loop.** Wrong passwords use the existing `failed_logins` counter. The fifth failure locks the account for 15 minutes and deletes the pending link. A locked account is rejected before bcrypt runs, and the pending link is also deleted then. The link is written in the same transaction that clears `failed_logins`.
- **Unlink (settings, not in the diagram).** Requires a session. If `password_hash` is NULL, refuse and point the user to the existing reset email to set a password. Otherwise delete the `google_identities` row for that user. No password is asked for the unlink.

## State

| Item | Where | Lifetime | Removed by |
|---|---|---|---|
| OIDC attempt: state, nonce, code_verifier, origin, next, user_id (settings) | Redis key `oidc:{state}` | TTL 600 s from start | `GETDEL` on any callback outcome, or TTL expiry |
| State cookie | Browser cookie, HttpOnly, Secure, SameSite=Lax, Max-Age 600 | Start to callback | Cleared on callback, or expiry |
| Pending link: sub, target user_id, origin, next | Redis key `pending:{id}` | TTL 600 s from creation | Deleted on success, lock or link conflict. Expiry. Kept on wrong password |
| Pending cookie | Browser cookie, same flags | Same as pending | Cleared with the pending record |
| Google link | PostgreSQL `google_identities` | Permanent | Unlink (settings, needs password), or user deletion (cascade). Not removed by sign-out, email change or password reset |
| Google-created user | `users` row with `password_hash` NULL and `email_verified_at` set | Permanent | User deletion. A password can be set later through the existing reset email |
| Failed count and lock | `users.failed_logins`, `users.locked_until` | Existing rules | Existing rules |
| Google tokens | Not stored. Held in memory during the callback only | Callback request | Discarded after reading the ID token |
| Session | `sessions` row and `sid` cookie | Existing | Existing rules. `start_session` removes any previous row |

## Schema change

```sql
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;  -- NULL for Google-created users

CREATE TABLE google_identities (
  sub       TEXT PRIMARY KEY,                                          -- Google subject id, max 255 chars; one user per Google account
  user_id   BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE, -- one Google account per user
  linked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Password login must treat a NULL `password_hash` as a failed password, with the same generic message and the same failure count. It must not call bcrypt on NULL.

## Failure summary

| Failure | What the user sees | State changed |
|---|---|---|
| Unknown, expired or used state | Error page | None |
| Google error (Cancel) | Origin page, neutral message | Attempt spent |
| Code exchange fails | Origin page, neutral try again | Attempt spent |
| ID token invalid (signature, iss, aud, exp, nonce) | Error page | Attempt spent |
| Unlinked, unverified email | Refusal, point to email and password | None |
| Unlinked sub already linked to another user (settings) | Refusal | None |
| Settings: session gone at callback | Login page, neutral message | None |
| Pending expired | Restart page | None |
| Wrong password | Wrong password message | failed_logins + 1, pending kept |
| Locked | Account temporarily locked | Pending deleted. Password not checked |
| Link conflict at insert (race) | Refusal | Transaction rolled back, pending deleted |
| Redis unavailable | Neutral error | No attempt created, so nothing is linked. Fails closed |

Redis restarts lose in-flight attempts. Users restart the flow, which is acceptable.

## Assumptions to confirm

1. Settings linking also refuses an unverified Google email. The brief's rule is written for unlinked subs in general, so this applies it to both entry points.
2. A linked user can still sign in with Google while the account is password-locked. The lock is about password guessing, so Google sign-in is not blocked. Confirm this.
3. Linking to an existing user does not change `email_verified_at`.
4. Pressing Cancel on the password form deletes the pending link. This is optional, since the TTL covers it.