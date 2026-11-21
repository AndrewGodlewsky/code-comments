# Sign in with Google: flow and state

This adds Google sign-in (OpenID Connect, authorization-code flow with PKCE, `state`, `nonce`, scopes `openid email profile`) beside password login. Google accounts are identified only by `sub`. Every successful Google sign-in calls the existing `start_session`, so the result is the same session as a password login.

Two entry points: the login page (sign in) and Account Settings (link, while signed in). Both use the same start and callback routes. The attempt record says which one started it.

```mermaid
flowchart TD
    LOGIN["Login page: Sign in with Google"] --> STRT
    SETTINGS["Account Settings: Link Google, signed in"] --> STRT
    STRT["GET /auth/google/start<br/>Create attempt in Redis, TTL 600 s<br/>Set goauth_state cookie to state"] --> GOOG["Redirect to Google<br/>PKCE S256, state, nonce<br/>scope openid email profile"]
    GOOG --> CB["GET /auth/google/callback"]

    CB --> CK{"goauth_state cookie equals state?"}
    CK -- no --> ERR1["Error page<br/>Nothing changes, attempt not consumed"]
    CK -- yes --> GD{"Attempt found? GETDEL<br/>unknown, expired or used?"}
    GD -- no --> ERR1
    GD -- yes --> GE{"Google sent an error param?"}
    GE -- yes --> BACK["Redirect to return_to with neutral message<br/>Nothing changes"]
    GE -- no --> EX["POST to Google token endpoint<br/>code plus code_verifier"]
    EX -- "timeout, network, non-200, invalid_grant" --> ERR2["Error page: could not finish with Google<br/>Nothing changes, user must start again"]
    EX -- ok --> VAL{"ID token valid?<br/>signature, iss, aud, exp, nonce"}
    VAL -- no --> ERR2
    VAL -- yes --> READ["Read sub, email, email_verified<br/>Discard Google tokens"]
    READ --> MODE{"Attempt mode?"}

    MODE -- settings --> SESS{"Session valid and same user as attempt?"}
    SESS -- no --> ERR3["Redirect to login with neutral message<br/>Nothing changes"]
    SESS -- yes --> LSUB{"sub already linked?"}
    LSUB -- "to this same user" --> SAME["Redirect to settings: already linked<br/>Nothing changes"]
    LSUB -- "to another user" --> REF1["Redirect to settings: Google account in use<br/>Nothing changes"]
    LSUB -- no --> HASG{"This user already has a Google account?"}
    HASG -- yes --> REF2["Redirect to settings: a different Google account is already linked<br/>Nothing changes"]
    HASG -- no --> INS1["INSERT google_identities sub, this user<br/>No password asked, email ignored"]
    INS1 --> DONES["Redirect to settings: Google linked<br/>No new session"]

    MODE -- login --> SUB0{"sub in google_identities?"}
    SUB0 -- yes --> LOCK{"Linked user locked_until in future?"}
    LOCK -- yes --> ERR4["Account temporarily locked<br/>No session"]
    LOCK -- no --> SESSION
    SUB0 -- no --> VER{"email_verified true?"}
    VER -- no --> REF3["Refuse: sign in with email and password<br/>Nothing created"]
    VER -- yes --> MATCH{"Lowercased email matches a user?"}
    MATCH -- no --> NEWU["Transaction: INSERT users with lowercased email, password_hash NULL, email_verified_at now<br/>INSERT google_identities sub, new user"]
    NEWU -- "unique clash on email or sub" --> RETRY["Race: re-read once, then refuse if still conflicting"]
    RETRY --> MATCH
    NEWU --> SESSION
    MATCH -- yes --> HASG2{"That user already has a Google account?"}
    HASG2 -- yes --> REF4["Refuse: account already linked to a different Google account<br/>Nothing changes"]
    HASG2 -- no --> PEND["Create pending link in Redis, TTL 600 s from callback<br/>Set goauth_pending cookie<br/>Store sub, user U, next"]
    PEND --> FORM

    FORM["Show password form for U<br/>Shows 10 minute window"] --> POST2["POST /auth/google/confirm"]
    POST2 --> PL{"Cookie matches a live pending link?"}
    PL -- no --> EXP["Error page: link expired, start again<br/>Delete pending link if present"]
    PL -- yes --> PLK{"U locked_until in future?"}
    PLK -- yes --> DROP1["Account temporarily locked<br/>Password not checked<br/>Delete pending link"]
    PLK -- no --> BC{"bcrypt password matches?"}
    BC -- no --> FAIL["failed_logins plus 1<br/>At 5: locked_until now plus 15 min, failed_logins 0"]
    FAIL --> LOCKED{"Account now locked?"}
    LOCKED -- yes --> DROP2["Delete pending link: half-finished link thrown away<br/>Show Account temporarily locked"]
    LOCKED -- no --> WRONG["Show generic wrong password message<br/>Pending link stays until its 10 minutes end"]
    WRONG --> FORM
    BC -- yes --> RECHK{"Transaction: U still has no Google account and sub still unlinked?"}
    RECHK -- no --> REF5["Refuse: link no longer possible<br/>Delete pending link"]
    RECHK -- yes --> OK2["failed_logins 0<br/>INSERT google_identities sub, U<br/>Set email_verified_at if null<br/>Delete pending link"]
    OK2 --> SESSION

    SESSION["start_session U, as for password login<br/>Delete old sid row, INSERT sessions, set sid cookie<br/>Redirect to next if relative, else /home"]

    UN["Settings: Unlink Google<br/>POST /settings/google/unlink"] --> HASPW{"U has a password_hash?"}
    HASPW -- no --> UREF["Refuse: set a password first<br/>Point to Forgot password reset email"]
    HASPW -- yes --> UDEL["DELETE google_identities row for U<br/>Sessions unchanged"]
```

## Notes

**Entry and callback.** Start stores the attempt in Redis under a hash of `state`, with the nonce, the PKCE verifier, the mode (`login` or `settings`), the `next` or return path, and for settings the linking user id and session id. The callback checks the `goauth_state` cookie first, so a crafted link from another browser cannot start a link or sign-in in the victim's browser. Only then does it consume the attempt with an atomic GETDEL. The first callback consumes the attempt whatever happens next, so a replay gets the error page. Attempts expire after 600 s, which covers the round trip to Google. If Redis is unavailable, the callback fails closed with the error page.

**Failed code exchange.** The attempt is already consumed, so the user must start again. The error page shows neutral text. Nothing is written, and no tokens are kept, including any that Google did return.

**Password confirmation.** The pending link lives 600 s from the callback and is not extended by retries. Wrong passwords use the existing counter and lock rules, so a wrong password here and a wrong password at `/login` share one counter. Locking deletes the pending link. A lock check runs before each password check, and while locked the password is not checked.

**Settings link.** The email is not used for matching, so an unverified Google email does not block it. The user does not get a new session.

**Unlink.** The `password_hash IS NULL` check and the DELETE should be one statement, so the rule holds under concurrent requests. Unlinking does not end sessions.

## State and where it lives

| Piece of state | Where | Lifetime | Removed by |
|---|---|---|---|
| Attempt: state hash, nonce, PKCE verifier, mode, return path, settings user and session | Redis `goauth:attempt:<sha256(state)>` | TTL 600 s from start | GETDEL at first callback, or TTL |
| `goauth_state` cookie (equals state) | Browser, HttpOnly, Secure, SameSite=Lax, Path=/auth/google | Max-Age 600 s | Cleared at callback, or expiry |
| Pending link: sub, candidate user U, next | Redis `goauth:pending:<random id>` plus `goauth_pending` cookie | TTL 600 s from callback, not sliding | Success, lock, failed re-check, expired-on-POST, or TTL |
| Google identity: `google_identities(sub PK, user_id UNIQUE, linked_at)` | Postgres, permanent | Until removed | Settings unlink (password users only), user deletion (cascade) |
| Google-created user: email lowercased, `password_hash` NULL, `email_verified_at` set | `users`, permanent | Until account deletion | Account deletion only |
| Lockout: `failed_logins`, `locked_until` | `users` | Existing rules | Existing rules |
| Session: `sessions` row and `sid` cookie | Postgres and browser | 14 days, slid on each request | Sign-out, password reset, account deletion, or the next start_session for the same browser |

No Google access or refresh token is stored anywhere. Google never changes `users.email`. Lookups use `sub`, so a changed Google email still reaches the same account.

## Failure outcomes

| Trigger | Outcome | Changes |
|---|---|---|
| Missing cookie, mismatched state, unknown, expired or used state | Error page | None; attempt not consumed on cookie mismatch |
| Google error param (e.g. Cancel), valid state | Back to start with neutral message | None |
| Settings: session gone or different user | Redirect to login, neutral message | None |
| Token exchange failure or timeout | Error page, start again | None |
| ID token invalid (signature, iss, aud, exp, nonce) | Error page | None; tokens discarded |
| Linked sub, locked account (login) | Account temporarily locked | None |
| Unlinked sub, `email_verified` false | Refuse, use email and password | None |
| Unlinked sub, no email match | Create user, link, sign in | users, google_identities, sessions |
| Unlinked sub, email match, user already has a Google account | Refuse | None |
| Wrong password | Generic message, counter +1 | failed_logins |
| Fifth wrong password | Lock, pending deleted | failed_logins, locked_until |
| Correct password, re-check fails | Refuse, pending deleted | None |
| Correct password | Link, sign in | google_identities, users, sessions |
| Settings: sub linked to this user | Already linked | None |
| Settings: sub linked to someone else, or user has a different Google account | Refuse | None |
| Unlink without a password | Refuse, use Forgot password | None |

## Changes to existing behaviour

- **Schema.** Drop NOT NULL on `users.password_hash`. Add `google_identities` as above. Google-only users always keep a link, because unlink needs a password. This keeps every account reachable.
- **POST /login.** When `password_hash` is NULL, return the generic message. Treat it as a wrong attempt, so behaviour does not reveal whether the account is Google-only.
- **Password reset.** Unchanged. It sets the hash for Google-created users and marks the email verified.

## Decisions to confirm

1. **Lockout and Google sign-in.** This document blocks a linked Google sign-in while `locked_until` is in the future. The brief does not say. Blocking is the conservative choice, but it means a password lockout also blocks Google for 15 minutes.
2. **`email_verified_at` on link.** This document sets it when a verified Google email links to an existing user. Confirm this is acceptable.
3. **NULL hash counts as a failed login.** Confirm that this counts toward lockout, as above.