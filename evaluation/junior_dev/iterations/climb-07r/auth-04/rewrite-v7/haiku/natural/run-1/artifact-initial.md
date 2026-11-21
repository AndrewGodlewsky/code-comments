# Sign in with Google: flow and state plan

This plan adds Google sign-in (OpenID Connect, authorization-code flow with PKCE) beside email and password. It builds on `users`, `sessions`, `start_session`, and the lockout rules in the existing files. Google sign-in ends in the same `start_session` call that password login uses.

## Flowchart

```mermaid
flowchart TD
    LP["Login page: Sign in with Google button"] --> START["POST /auth/google/start<br/>Create state, nonce, PKCE code_verifier<br/>Redis oidc:tx:state with TTL 600 s<br/>Set cookie oidc_tx = state"]
    SET["Account Settings: Link Google button<br/>(requires session and CSRF token)"] --> SLINK["POST /settings/google/link<br/>Same Redis record, intent link, user_id"]
    START --> AUTHZ["Redirect to Google authorize<br/>scope openid email profile, PKCE S256, nonce"]
    SLINK --> AUTHZ
    AUTHZ --> CB["GET /auth/google/callback"]
    CB --> C1{"Redis GETDEL oidc:tx:state found<br/>and oidc_tx cookie matches?"}
    C1 -->|"no: unknown, expired or already used"| E_STATE["Error page. Nothing changes"]
    C1 -->|"yes: record deleted now"| C2{"Google returned an error parameter?"}
    C2 -->|"yes, e.g. user pressed Cancel"| N_CANCEL["Redirect to return_to with neutral message"]
    C2 -->|no| C3{"Code exchange with code_verifier succeeds<br/>and ID token passes signature, iss, aud, exp, nonce checks?"}
    C3 -->|"no: network error, Google 4xx, bad token"| E_EXCH["Error page: sign-in failed, try again<br/>Nothing written. Record already deleted"]
    C3 -->|yes| C4{"intent?"}

    C4 -->|link| L1{"Signed-in user equals intent user_id?"}
    L1 -->|no| E_SESS["Error page. Nothing changes"]
    L1 -->|yes| L2{"sub already in google_identities?"}
    L2 -->|"yes, same user"| N_SAME["Settings: already linked"]
    L2 -->|"yes, another user"| E_OTHER["Settings: refuse. Linked to someone else"]
    L2 -->|no| L3{"This user already has a Google account?"}
    L3 -->|yes| E_DIFF["Settings: refuse. A different Google account is linked"]
    L3 -->|no| L4["INSERT google_identities sub, user_id<br/>Settings: linked"]

    C4 -->|login| M1{"sub found in google_identities?"}
    M1 -->|yes| M2{"Linked user locked_until in future?"}
    M2 -->|yes| E_LOCK["Account temporarily locked. No session"]
    M2 -->|no| SS["start_session user_id, same as password login<br/>Redirect to next or /home"]
    M1 -->|no| M3{"email_verified true?"}
    M3 -->|no| E_UNVER["Refuse: use email and password. Nothing created"]
    M3 -->|yes| M4{"Lowercased email matches a users row?"}
    M4 -->|no| NEW["One DB transaction: INSERT users with NULL password_hash<br/>and email_verified_at = now, then INSERT google_identities"]
    NEW --> SS
    M4 -->|yes| M5{"Matched user already has a Google account?"}
    M5 -->|yes| E_HAS["Refuse: that account already has a different Google account"]
    M5 -->|no| PEND["Redis oidc:pending:id, TTL 600 s from callback<br/>holds sub and user_id. Set cookie oidc_pending<br/>Show password form"]

    PEND --> PF["User submits password<br/>POST /auth/google/confirm, CSRF protected"]
    PF --> P1{"Pending record exists and cookie matches?"}
    P1 -->|"no: expired or gone"| E_PEND["Error page: start sign-in again"]
    P1 -->|yes| P2{"locked_until in future?"}
    P2 -->|yes| D_LOCK0["DELETE pending record. Show Account temporarily locked. No link"]
    P2 -->|no| P3{"bcrypt matches password_hash?"}
    P3 -->|no| P4["failed_logins plus 1<br/>at 5: set locked_until to now plus 15 min, failed_logins to 0"]
    P4 --> P5{"Account now locked?"}
    P5 -->|yes| D_LOCK1["DELETE pending record. Show Account temporarily locked. No link"]
    P5 -->|no| PWRONG["Show generic wrong-password message<br/>Pending record stays until its TTL"]
    PWRONG --> PF
    P3 -->|yes| P6["failed_logins set to 0<br/>One DB transaction: INSERT google_identities, then DELETE pending record"]
    P6 --> SS

    SET2["Account Settings: Unlink Google<br/>POST /settings/google/unlink, session and CSRF"] --> U1{"password_hash is NULL?"}
    U1 -->|yes| U_NO["Refuse: set a password first using the existing reset email"]
    U1 -->|no| U2["DELETE google_identities row for this user<br/>Sessions unchanged"]
```

## Where new state lives

Permanent (PostgreSQL):

- `users.password_hash`: becomes nullable. Google-created users have NULL. It is set by the existing reset flow and never removed.
- `google_identities` (new): one row per linked Google account. It is created when a link succeeds (login creation, password confirmation, or settings). It is removed by unlink (only for users with a password) or by user deletion (cascade). Sign-out, session expiry and password reset do not remove it.
- Google email and any Google tokens are never stored. `users.email` is never changed by Google sign-in.

Temporary (Redis, plus browser cookies):

- `oidc:tx:state` (Redis): holds code_verifier, nonce, intent (login or link), user_id for link, and a validated relative return_to. Created at start with TTL 600 s. Deleted atomically with GETDEL at the first callback, so a replayed callback finds nothing.
- Cookie `oidc_tx` (HttpOnly, Secure, SameSite=Lax, max age 600 s): holds the state value. The callback requires it to match. Cleared at callback.
- `oidc:pending:id` (Redis): holds sub and matched user_id. Created only in the password-confirmation branch. TTL 600 s from callback. Deleted on success, on lockout, or by TTL.
- Cookie `oidc_pending`: same lifetime as the pending record. Cleared when the record is deleted.
- `sessions` row: created by `start_session`, same as password login.
- `users.failed_logins` and `users.locked_until`: existing columns. The Google password confirmation shares the same counter.

Migration:

```sql
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

CREATE TABLE google_identities (
  sub        TEXT PRIMARY KEY,                          -- Google account id
  user_id    BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  linked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

The primary key on `sub` enforces one user per Google account. The unique `user_id` enforces one Google account per user. Both are backstops for the checks in the flowchart and for races.

## Failure behaviour

- Unknown, expired or reused state (or cookie mismatch): error page. Nothing is read or written beyond the failed GETDEL.
- Google error parameter, such as Cancel: the record is already consumed. The user is redirected to return_to with a neutral message.
- Failed code exchange (network error, 4xx such as invalid_grant, or ID token check failure): error page. Nothing is written. The state is spent, so the user starts again from the login or settings page.
- Redis unavailable: fail closed. Show an error page and do not create state or accounts.
- Unlinked sub with email_verified false: refuse, point to email and password. Nothing is created.
- Unlinked sub with a verified email that matches no user: create the user and link in one transaction, then sign in. A concurrent duplicate email fails the unique constraint and returns an error page with no partial rows.
- Matched user already has a Google account: refuse before any password prompt.
- Wrong password: failed_logins + 1 with the existing lock rule. The pending record stays until TTL so the user can retry.
- Lock reached during confirmation: delete the pending record. Nothing is linked. The user sees Account temporarily locked.
- Pending expired: error page, start again.
- Settings link, Google account used by someone else or already linked to this user: refuse with a message. Nothing changes.
- Settings unlink, no password: refuse. The message points to the existing reset email.

## Decisions for the owner

- Browser binding (`oidc_tx` cookie): not in the brief. Without it, an attacker can start a flow with their own Google account and make a victim's browser complete it. Recommended.
- Locked accounts and Google sign-in: the flowchart rejects linked-user Google login while `locked_until` is in the future, so a lock cannot be bypassed. Google sign-in does not increment the counter.
- Email verification on confirmation: on a correct password, set `email_verified_at` if it is NULL, since Google has verified the email. Not in the brief.
- Settings linking does not check `email_verified`. The brief does not require it, and linking uses only `sub`.
- Unlink does not end sessions. Confirm this is wanted.
- Password login must reject NULL `password_hash` with the same generic message, and still run a dummy bcrypt compare so timing does not reveal the account type. The confirmation path never reaches a NULL hash, because a Google-created user always has a link, which blocks the confirmation branch at M5.
- Return_to is validated as a relative path on our site at start and again before redirect.
- Confirmation form posts are CSRF protected, same as the settings forms.