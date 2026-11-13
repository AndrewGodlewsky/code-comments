# Sign in with Google: flow and state design

Google sign-in (OpenID Connect, authorization-code flow with PKCE) sits beside email and password. Both entry points, the login page and Account Settings, share one callback. Every successful Google sign-in ends in the same session as a password login, through the existing `start_session(user_id)`.

Terms used below:
- **Attempt**: a short-lived Redis record created when the flow starts and deleted by the first callback.
- **Confirm record**: a short-lived Redis record for the password step, used when an unlinked Google account matches an existing user's verified email.
- **Link**: a `google_identities` row tying one Google `sub` to one user.

## Flowchart

```mermaid
flowchart TD
    subgraph EP["Entry points"]
        A1["Login page: Sign in with Google"]
        A2["Account Settings: Link Google (session required)"]
        A1 --> B1["Redis attempt: state, nonce, PKCE verifier, mode login, next path<br/>TTL 600 s. Cookie gx = state"]
        A2 --> B2["Redis attempt: same fields, mode link, user_id = session user<br/>TTL 600 s. Cookie gx = state"]
    end
    B1 --> G["Redirect to Google: code flow, PKCE S256, scope openid email profile"]
    B2 --> G
    G --> CB["Google redirects to GET /auth/google/callback"]

    CB --> Q1{"error param present?"}
    Q1 -->|"yes"| Q1A{"gx cookie = state and attempt exists?"}
    Q1A -->|"no"| ERR["Error page. No change."]
    Q1A -->|"yes"| CAN["Delete attempt, clear gx. Redirect to next with neutral message: Google sign-in cancelled"]
    Q1 -->|"no"| Q2{"gx cookie = state and GETDEL attempt returns a value?"}
    Q2 -->|"no: unknown, expired or already used"| ERR
    Q2 -->|"yes"| X1["Server POST to Google token endpoint with code and PKCE verifier. Keep id_token only, drop access and refresh tokens"]
    X1 -->|"network error, timeout or non-200"| XERR["Error page with try-again link. No change."]
    X1 -->|"ok"| V1{"ID token valid? signature, iss, aud = our client id, exp, nonce = attempt nonce"}
    V1 -->|"no"| XERR
    V1 -->|"yes: read sub, email, email_verified"| MODE{"attempt mode?"}

    MODE -->|"link"| LS{"session valid and user = attempt user_id?"}
    LS -->|"no"| ERR
    LS -->|"yes"| L1{"sub already linked?"}
    L1 -->|"to this user"| LDONE["Redirect to settings: already linked"]
    L1 -->|"to another user"| LREF1["Redirect to settings: refused, Google account belongs to another account"]
    L1 -->|"no"| L2{"this user already has a Google link?"}
    L2 -->|"yes"| LREF2["Redirect to settings: refused, one Google account per user"]
    L2 -->|"no"| LINK["Insert google_identities row. Redirect to settings: Google linked. No password asked. Email need not match."]

    MODE -->|"login"| S1{"sub linked to a user?"}
    S1 -->|"yes"| S2{"that user locked_until in future?"}
    S2 -->|"yes"| SLOCK["Redirect to login: Account temporarily locked"]
    S2 -->|"no"| SESS["start_session for linked user"]
    S1 -->|"no"| S3{"email_verified true?"}
    S3 -->|"no"| SREF["Redirect to login: sign in with email and password instead. Nothing created."]
    S3 -->|"yes"| S4{"user with this lowercased email exists?"}
    S4 -->|"no"| NEW["Create user: password_hash NULL, email_verified_at = now. Insert google_identities. start_session."]
    S4 -->|"yes"| S5{"that user already has a Google link?"}
    S5 -->|"yes, to another sub"| SREF2["Redirect to login: refused, that account already has a Google account"]
    S5 -->|"no"| PEND["Redis confirm record: sub, user_id, next. TTL 600 s from callback. Cookie gconfirm = cid. Show password form."]

    PEND --> PW["User submits password: POST /login/google/confirm"]
    PW --> P1{"confirm record and gconfirm cookie present?"}
    P1 -->|"no: expired or cancelled"| PEXP["Redirect to login: link expired, start again"]
    P1 -->|"yes"| P2{"account locked_until in future?"}
    P2 -->|"yes"| PLOCK["Delete confirm record, clear cookie. Show: Account temporarily locked. Password not checked."]
    P2 -->|"no"| P3{"bcrypt password correct?"}
    P3 -->|"no"| P4{"failed_logins + 1 = 5?"}
    P4 -->|"no"| P5["Save failed_logins + 1. Show incorrect password. Form stays open until record TTL ends."]
    P5 --> PW
    P4 -->|"yes"| PLOCK2["Set locked_until = now + 15 min, failed_logins = 0. Delete confirm record, clear cookie. Show locked message."]
    P3 -->|"yes"| P6{"one transaction: sub still unlinked and user has no Google link?"}
    P6 -->|"no"| PREF["Delete confirm record, clear cookie. Redirect to login: refused, nothing linked."]
    P6 -->|"yes"| P7["Set failed_logins = 0. Insert google_identities. Commit."]
    P7 --> P8["Delete confirm record, clear cookie. start_session for user."]

    NEW --> OK
    SESS --> OK
    P8 --> OK
    OK["Same session as password login: sessions row, sid cookie, redirect to next or /home"]
```

Unlink from Account Settings (separate flow):

```mermaid
flowchart TD
    U1["Settings: Unlink Google (session required, CSRF-protected POST)"] --> U2{"users.password_hash IS NULL?"}
    U2 -->|"yes"| U3["Refuse: set a password first. Use Forgot password; the reset email sets one."]
    U2 -->|"no"| U4["Delete this user's google_identities row. Sessions unchanged."]
```

## Notes

**Schema change.** Google-created users have no password, so `password_hash` must become nullable. The migration is:

```sql
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

CREATE TABLE google_identities (
  google_sub TEXT PRIMARY KEY,                                                    -- one Google account links to at most one user
  user_id    BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,       -- a user has at most one Google account
  linked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Login must now handle a NULL `password_hash`. Return the existing generic message, and run a dummy bcrypt compare so timing does not reveal the difference.

Identity is keyed by `sub` only. Google's email is read at sign-in and never written to `users.email`. A linked user whose Google email changes still resolves to the same account.

**Where state lives**

| State | Where | Holds | Created | Removed by | Lifetime |
|---|---|---|---|---|---|
| Attempt | Redis `goauth:attempt:{state}` | mode, user_id (link only), nonce, PKCE verifier, next path | Flow start | Callback `GETDEL`, valid or not; otherwise Redis TTL | 600 s from start |
| Cookie `gx` | Browser (HttpOnly, Secure, SameSite=Lax) | state value | Flow start | Callback clears it; Max-Age 600 | 600 s |
| Confirm record | Redis `goauth:confirm:{cid}` | google_sub, target user_id, next path | Unlinked sub matches an existing verified email | Success, lockout, cancel, or TTL | 600 s from callback; wrong passwords do not extend it |
| Cookie `gconfirm` | Browser (HttpOnly, Secure, SameSite=Lax) | cid (32 random bytes, base64url) | Same as confirm record | Same as confirm record | Same as confirm record |
| Google-created user | Postgres `users` | lowercased email, `email_verified_at = now()`, NULL password_hash | Verified email matches no user | Account deletion | Permanent |
| Link | Postgres `google_identities` | sub, user_id | Link success | Unlink; user deletion cascades | Permanent |
| Lockout | Postgres `users.failed_logins`, `locked_until` | existing fields | Wrong password | Existing rules | Existing rules |
| Session | Postgres `sessions` plus `sid` cookie | existing | `start_session` | Existing rules | Existing rules |

No Google access or refresh token is stored. The token response is read for `id_token` and then dropped.

**Failure outcomes**

| Failure | User sees | What changes |
|---|---|---|
| State unknown, expired or already used | Error page | Nothing |
| Google error param, state valid | Back at start, neutral "Google sign-in cancelled" | Attempt deleted |
| Google error param, state invalid | Error page | Nothing |
| Code exchange fails (network, timeout, non-200, invalid_grant) | Error page with try-again link | Nothing. The attempt was already consumed, so the code cannot be replayed. |
| ID token invalid (signature, iss, aud, exp, nonce) | Error page | Nothing |
| Unlinked, email_verified false | Login page: use email and password | Nothing created |
| Link: sub belongs to another user | Settings: refused | Nothing |
| Link: user already has another Google account | Settings: refused | Nothing |
| Confirm: wrong password | "Incorrect password", form stays open | failed_logins + 1 |
| Confirm: 5th wrong password | "Account temporarily locked" | Lock set, confirm record deleted |
| Confirm: account already locked | "Account temporarily locked", password not checked | Confirm record deleted |
| Confirm: record expired or cancelled | Login page: link expired | Nothing |
| Confirm: race, sub linked or user got a Google link meanwhile | Login page: refused | Confirm record deleted, nothing linked |
| Insert hits a unique constraint (google_sub, user_id) | Refused, as above | Transaction rolled back |
| Create user hits users.email unique constraint (concurrent sign-up) | Re-run the email lookup once | Nothing from the failed insert |
| Redis unavailable | Error page | Nothing (fail closed) |

**Choices beyond the brief (for review)**

1. The `gx` cookie binds the attempt to the browser that started it. Without it, an attacker could start a flow and send the victim the callback URL. In settings mode that would link the attacker's Google account to the victim's user.
2. Linked Google sign-in honours `locked_until`, which matches password rules. The brief is silent on this. The alternative is to let Google bypass the lock.
3. Linking from settings does not require `email_verified`. The brief allows unmatched emails, and the user is already signed in.
4. Reaching the lock on the password step, or finding the account already locked, deletes the confirm record. This applies "throw away the half-finished link" to both cases.
5. The confirm page has a cancel action that deletes the confirm record and clears `gconfirm`.
6. The confirm POST and the settings link and unlink POSTs use the same CSRF protection as the existing login form.
7. A password reset sets `password_hash`, which is the only way for a Google-only user to get a password. Unlink then becomes allowed.