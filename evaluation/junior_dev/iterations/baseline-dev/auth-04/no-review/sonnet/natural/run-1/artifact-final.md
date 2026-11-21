# Sign in with Google: flow and state

Read this section first if you haven't seen the existing code. Passwords work as in `auth_flow.md`: `POST /login`, the 5-failure lockout for 15 minutes, and `start_session(user_id)`, which creates the `sessions` row and the `sid` cookie. Google sign-in adds one new table and some short-lived Redis keys. It changes nothing else.

## Where state lives

**Permanent (PostgreSQL)**

```sql
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;  -- NULL = Google-only user

CREATE TABLE user_google_accounts (
  user_id    BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, -- a user has at most one Google account
  google_sub TEXT NOT NULL UNIQUE,                                      -- a Google account links to at most one user
  linked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- We store no email, token or profile data here. Lookup is by `google_sub` only, so a changed Google email changes nothing.
- A row is removed by Unlink or by deleting the user (cascade). Nothing else removes it.
- Code that reads `password_hash` must treat NULL as "no password". A password login against a NULL hash counts as a wrong password and takes the same generic failure path. It must not crash.
- Password reset needs no change. It sets `password_hash`, which is how a Google-only user gets a password.
- `users.email` is never written from Google data, except for the row created in the "new user" branch.

**Temporary (Redis, never PostgreSQL)**

| Key | Holds | Created | Removed by |
|---|---|---|---|
| `oidc:state:<sha256(state)>` | `code_verifier`, `nonce`, `mode` (`login` or `link`), `user_id` (link mode only), a random browser-binding value, sanitized `next` | when the user clicks the Google button | The callback reads and deletes it in one atomic step (`GETDEL`, Redis 6.2 or later), so a callback is honoured once. The 600 s TTL removes it if no callback comes. |
| `oidc:pending:<id>` | Google `sub`, target `user_id`, sanitized `next` | when the password-confirmation prompt is shown | On successful link, on account lock, on Cancel, on "refused" outcomes at confirm time, or after 600 s TTL. Wrong passwords do not extend the TTL. |

Two short-lived cookies carry these. Both are HttpOnly, Secure and SameSite=Lax:
- `oidc_bind`: the random binding value, set at start. The callback must present it. It stops someone else's callback URL from signing you in, and it is cleared at the callback.
- `oidc_pending`: the `<id>` of the pending record, set when the prompt is shown. It is cleared when the record is discarded.

The `sid` session, the `sessions` table and the lockout counters are unchanged.

## Notes on the flow

- **Start.** The login page entry is `GET /login/google`. The settings entry is a CSRF-protected `POST` from a signed-in session. Both run the same start step. `next` is checked with the same "relative path on our site" rule as `start_session` before it is stored. The authorize request uses `response_type=code`, PKCE `S256`, `state`, `nonce` and `scope=openid email profile`. If the Redis write fails, we do not redirect to Google. We show "try again" on the page the user came from.
- **Callback order matters.** The state is consumed first, even when Google reports an error. Only then do we branch. This way an unknown, expired or reused `state` always gets the error page, and a Cancel with a valid `state` returns the user to where they started.
- **ID token.** After the code exchange we verify the signature (Google JWKS), `iss`, `aud` (our client id), `exp` and that `nonce` equals the stored one. We read `sub`, `email` and `email_verified`, then drop the tokens. We keep no access or refresh token.
- **Both modes.** Every outcome that creates or links something does so in one database transaction. The unique constraints are the final guard. If a concurrent request trips one, the result is the matching "refused" outcome and nothing is half-written. The new-user insert is the exception: a unique violation there means a user with that email appeared meanwhile, so re-run the decision once and it falls into the confirm branch.
- **Settings link** is not a sign-in, so it calls no `start_session`. The existing session stays as it is. It needs no password and ignores email and `email_verified`. It requires the current session's user to equal the `user_id` stored at start. Otherwise it is the error page.
- **Unlink** is `POST /settings/google/unlink` from a signed-in session. It runs as a single `DELETE ... WHERE user_id = $1 AND EXISTS (password_hash IS NOT NULL)`. A user with no password sees "Set a password first, using the password reset email" (the existing `POST /forgot`).
- **Assumption to confirm.** A locked account is still reachable by Google sign-in when the `sub` is already linked. The lockout guards password guessing, and Google has proved identity. The brief doesn't say, so say so if you want it blocked.
- **Assumption to confirm.** Linking in the confirm loop does not change `email_verified_at` on the existing user.

## Flowchart

```mermaid
flowchart TD
  subgraph START["Start (two entry points)"]
    L0["Login page: click Sign in with Google"]
    S0["Account Settings: click Link Google<br/>POST, CSRF checked, user signed in"]
    S1["Create state, nonce, code_verifier, binding value<br/>Sanitize next<br/>Save Redis oidc:state, TTL 10 min<br/>Set oidc_bind cookie<br/>mode = login or link"]
    E0["Back to origin page:<br/>Google sign-in unavailable, try again<br/>No redirect to Google"]
    G["Redirect to Google authorize<br/>code flow, PKCE S256, state, nonce<br/>scope openid email profile"]
    L0 --> S1
    S0 --> S1
    S1 -->|Redis write fails| E0
    S1 --> G
  end

  G --> CB["GET /auth/google/callback"]

  subgraph CALLBACK["Callback: common to both modes"]
    C1{"GETDEL oidc:state for this state<br/>found AND oidc_bind cookie matches?"}
    EP["Error page<br/>Nothing changed, nothing created"]
    C2{"Google sent error param<br/>or no code?"}
    BACK["Redirect to origin page<br/>Neutral message: Google sign-in was not completed<br/>Nothing changed"]
    C3["POST token endpoint<br/>code + code_verifier"]
    C4{"Exchange succeeded AND ID token valid?<br/>signature, iss, aud, exp, nonce"}
    FAILX["Redirect to origin page<br/>Could not complete Google sign-in, try again<br/>Nothing changed<br/>State already used, code never retried"]
    C5["Read sub, email, email_verified<br/>Discard all tokens"]
    M{"mode stored in state"}
    CB --> C1
    C1 -->|"no: unknown, expired, used, or cookie mismatch"| EP
    C1 -->|yes| C2
    C2 -->|yes| BACK
    C2 -->|no| C3
    C3 --> C4
    C4 -->|no| FAILX
    C4 -->|yes| C5
    C5 --> M
  end

  subgraph LOGIN["mode = login"]
    D1{"sub in user_google_accounts?"}
    D2{"email_verified true?"}
    R1["Refuse, back to login page:<br/>use email and password<br/>Nothing created"]
    D3{"Lowercased email matches a users.email?"}
    NEW["One transaction:<br/>insert user, password_hash NULL, email_verified_at now<br/>insert user_google_accounts row"]
    D4{"Matched user already has<br/>a Google account linked?"}
    R2["Refuse, back to login page:<br/>that account has a different Google account<br/>Nothing changed"]
    P1["Save Redis oidc:pending, TTL 10 min<br/>Set oidc_pending cookie<br/>Show password form, with Cancel"]
    M -->|login| D1
    D1 -->|no| D2
    D2 -->|no| R1
    D2 -->|yes| D3
    D3 -->|no| NEW
    D3 -->|yes| D4
    D4 -->|yes| R2
    D4 -->|no| P1
  end

  subgraph CONFIRM["Password confirmation loop"]
    P2["POST password"]
    P3{"oidc:pending still exists?"}
    EP2["Error page: took too long, start again<br/>Nothing changed"]
    P4{"locked_until in the future?"}
    DISC["Delete oidc:pending, clear cookie<br/>Show: Account temporarily locked<br/>Nothing linked"]
    P5{"bcrypt matches?"}
    P6["failed_logins + 1<br/>at 5: locked_until = now + 15 min, failed_logins = 0"]
    P7{"Account now locked?"}
    P8["Show form again with generic wrong-password message<br/>Same pending record, same expiry"]
    P9["failed_logins = 0<br/>Transaction: insert link row, delete oidc:pending"]
    P10{"Unique violation?<br/>user or sub got linked meanwhile"}
    R3["Delete oidc:pending<br/>Refuse: already linked<br/>Nothing changed"]
    CAN["Cancel clicked:<br/>delete oidc:pending, back to login page"]
    P1 --> P2
    P1 -.-> CAN
    P2 --> P3
    P3 -->|no| EP2
    P3 -->|yes| P4
    P4 -->|yes| DISC
    P4 -->|no| P5
    P5 -->|wrong| P6
    P6 --> P7
    P7 -->|yes| DISC
    P7 -->|no| P8
    P8 --> P2
    P5 -->|right| P9
    P9 --> P10
    P10 -->|yes| R3
  end

  SI["start_session user_id<br/>Same session as password login<br/>Redirect to sanitized next, else /home"]
  D1 -->|yes| SI
  NEW --> SI
  P10 -->|no| SI

  subgraph LINK["mode = link (from Account Settings)"]
    K1{"Signed in AND session user_id<br/>equals user_id in state?"}
    K2{"sub already linked?"}
    K3{"This user already has<br/>a Google account?"}
    K4["Insert link row<br/>No session change"]
    K5{"Unique violation?"}
    KR1["Back to Settings: already linked to another account<br/>Nothing changed"]
    KR2["Back to Settings: Google already linked, no change"]
    KR3["Back to Settings: unlink the current Google account first<br/>Nothing changed"]
    KOK["Back to Settings: Google linked"]
    M -->|link| K1
    K1 -->|no| EP
    K1 -->|yes| K2
    K2 -->|"yes, to a different user"| KR1
    K2 -->|"yes, to this user"| KR2
    K2 -->|no| K3
    K3 -->|yes| KR3
    K3 -->|no| K4
    K4 --> K5
    K5 -->|yes| KR1
    K5 -->|no| KOK
  end

  subgraph UNLINK["Unlink (Settings, signed in)"]
    U0["POST /settings/google/unlink"]
    U1{"password_hash IS NOT NULL?"}
    U2["Delete link row<br/>Sessions untouched"]
    U3["Refuse: set a password first<br/>using the existing reset email"]
    U0 --> U1
    U1 -->|yes| U2
    U1 -->|no| U3
  end
```

## Failure summary

| Failure | What the user sees | State change |
|---|---|---|
| `state` unknown, expired (over 10 min), already used, or binding cookie missing or different | Error page | None. The record is consumed if it existed. |
| Google returned `error` (for example, Cancel) | Back to the login page or Settings, neutral message | None. The record is consumed. |
| Code exchange fails (network, timeout, non-200, `invalid_grant`) or ID token fails validation | Back to the origin page, "could not complete, try again" | None. The record is consumed, so the code is not retried. Log the cause server-side. |
| Redis unavailable at start | Origin page, "try again" | None. No redirect to Google. |
| Redis unavailable at callback or confirm | Error page | None. |
| Unverified Google email, unlinked `sub` | Login page, "use email and password" | None. Nothing is created. |
| Matched account already has another Google account | Login page, refusal | None. |
| Wrong password in confirm loop | Form again, generic message | `failed_logins + 1`. The pending record is kept. |
| Fifth wrong password, or already locked | "Account temporarily locked" | Lock set as in `POST /login`. Pending record deleted, so no link. |
| Over 10 minutes at confirm | Error page | Pending record has expired. Nothing linked. |
| Settings link: `sub` is linked to someone else | Settings, refusal | None. |
| Unlink with no password | Settings, "set a password first" | None. |
