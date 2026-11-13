# Sign in with Google: flow and state

## State this adds

- **`oidc:attempt:<state>`** (Redis, TTL 10 min). The start step writes it. It holds `mode` (`login` or `link`), `user_id` (link mode only), `nonce`, the PKCE `code_verifier` and `next`. The callback deletes it with an atomic GETDEL as its very first step, so only the first callback for a given `state` can use it. An unused one expires.
- **`oidc:pending:<id>`** (Redis, TTL 10 min). Written when a Google sign-in matches an existing password account. It holds `user_id`, `google_sub`, `google_email` and `next`. The browser holds only the random `<id>`, in an HttpOnly, Secure `pending_link` cookie. It is deleted when the link succeeds or the account locks, and otherwise expires.
- **`user_identities`** (new PostgreSQL table): `user_id, provider='google', subject (= Google sub), email_at_link, linked_at`.
  - `UNIQUE(provider, subject)` means a Google account links to only one user.
  - `UNIQUE(user_id, provider)` means a user has only one Google account. Settings shows "Link Google" only when the user has none.
- **`users.password_hash`** becomes nullable. NULL means a Google-only account. For such an account the password form returns its usual generic error.
- **Google tokens.** The access and refresh tokens from the code exchange are dropped at once. Only the ID token's `sub`, `email` and `email_verified` are read.

**Matching rule:** by `sub` only. Email is checked only when the `sub` is not linked. A linked user whose Gmail address has changed still lands in the same account. Google never changes our `users.email`.

## Flow

```mermaid
flowchart TD
  L0["Login page:<br/>Sign in with Google"] --> ST
  K0["Account settings, signed in:<br/>Link Google"] --> ST
  ST["Start: GET /auth/google/start<br/>make state, nonce, PKCE verifier<br/>SET Redis oidc:attempt:STATE, TTL 10 min"] --> GG
  GG["Browser goes to Google consent<br/>scopes openid email profile"] --> CB
  CB["Google sends browser back:<br/>GET /auth/google/callback with state and code"] --> C1
  C1{"GETDEL oidc:attempt:STATE<br/>record found?"}
  C1 -->|"no: unknown, expired or already used"| E1["Error page:<br/>sign-in expired or invalid, try again"]
  C1 -->|"yes"| C2{"Google sent an error?<br/>e.g. user pressed Cancel"}
  C2 -->|"yes"| E2["Back to login page or settings<br/>neutral message"]
  C2 -->|"no"| C3{"Exchange code + verifier for tokens<br/>check ID token: signature, iss, aud, exp, nonce"}
  C3 -->|"fails"| E3["Redirect to /login:<br/>Google sign-in failed, try again"]
  C3 -->|"ok: keep sub, email, email_verified"| C4{"attempt mode?"}

  subgraph SG_LINK["Link from settings, mode = link"]
    K1{"session user = attempt user_id?"}
    K2{"sub in user_identities?"}
    K3["INSERT user_identities<br/>no password asked, emails may differ"]
    E4["Settings: this Google account is<br/>linked to another account"]
    K4["Settings: already linked"]
    K5["Settings: Google linked"]
  end

  subgraph SG_LOGIN["Sign in, mode = login"]
    M1{"sub in user_identities?"}
    M2{"email_verified?"}
    E5["Redirect to /login:<br/>use email and password"]
    M3{"users row with this email, lowercased?"}
    N1["One transaction:<br/>INSERT users, password_hash NULL, email_verified_at now<br/>INSERT user_identities"]
    E6["Redirect to /login:<br/>that account is linked to a different Google account"]
    P1["SET Redis oidc:pending:ID, TTL 10 min<br/>set pending_link cookie = ID<br/>show Confirm your password"]
  end

  subgraph SG_CONF["Password confirmation, existing lockout rules"]
    P2["User submits password:<br/>POST /auth/google/confirm"]
    P3{"pending record found?"}
    E7["Redirect to /login:<br/>link expired, start again"]
    P4{"locked_until in the future?"}
    P5{"bcrypt check"}
    P6["DEL pending, clear cookie<br/>show Account temporarily locked"]
    P7["failed_logins + 1<br/>at 5: locked_until = now + 15 min, counter reset"]
    P8["failed_logins = 0<br/>INSERT user_identities<br/>DEL pending, clear cookie"]
  end

  SS["Existing start_session for the user<br/>delete old sid row, new sessions row, sid cookie 14 days<br/>redirect to next or /home"]

  C4 -->|"link"| K1
  K1 -->|"no"| E1
  K1 -->|"yes"| K2
  K2 -->|"yes, another user"| E4
  K2 -->|"yes, this user"| K4
  K2 -->|"no"| K3
  K3 --> K5

  C4 -->|"login"| M1
  M1 -->|"yes"| SS
  M1 -->|"no"| M2
  M2 -->|"false"| E5
  M2 -->|"true"| M3
  M3 -->|"no match"| N1
  N1 --> SS
  M3 -->|"match, has another Google link"| E6
  M3 -->|"match, no Google link"| P1
  P1 --> P2
  P2 --> P3
  P3 -->|"no: expired"| E7
  P3 -->|"yes"| P4
  P4 -->|"yes"| P6
  P4 -->|"no"| P5
  P5 -->|"wrong"| P7
  P7 -->|"5th wrong, now locked"| P6
  P7 -->|"under 5: show form again"| P2
  P5 -->|"right"| P8
  P8 --> SS
```

## Failure rules

- **Error exits write nothing.** Every error exit leaves no user, no link and no session.
- **Code exchange or ID-token check fails.** This covers a Google error or timeout, a bad signature, a wrong `iss` or `aud`, an expired token and a nonce mismatch. The exchange is not retried, because the code is single-use and the attempt record is already gone. The user starts again from the button.
- **Signature keys.** ID-token signatures are checked against Google's published keys (JWKS), cached for as long as Google's Cache-Control allows.
- **Wrong passwords during confirmation.** Confirmation uses the existing counters on `users` (`failed_logins`, `locked_until`). The 5th wrong password locks the account for 15 minutes and deletes the pending link. The user must start Google sign-in again after the lock.
- **Unlink (settings).** Allowed only if `password_hash` is not NULL. Otherwise the page tells the user to set a password with the existing reset email first. Unlinking deletes the `user_identities` row. Current sessions are kept.

## Session

Every success ends in the existing `start_session(user_id)`:

1. Delete the sessions row for any `sid` the browser already had.
2. Insert a new `sessions` row and set the `sid` cookie (HttpOnly, Secure, SameSite=Lax, 14 days, slid forward on use).
3. Redirect to `next` if it is a relative path on our site, otherwise to `/home`.
