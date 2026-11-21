# Sign in with Google: flow, state and failures

This plan builds on the existing password login. Google sign-in ends in the same `start_session(user_id)` call, and wrong passwords use the existing `failed_logins` and `locked_until` rules. Two things are new: a short-lived flow held in Redis and a `google_identities` table. Google accounts are matched only by `sub`.

The flowchart is the source of truth. The tables below it say where each piece of state lives and what removes it.

```mermaid
flowchart TD
  subgraph ENTRY["Entry points"]
    LOGIN["Login page: Sign in with Google button"]
    SETTINGS["Account Settings: Link Google button, POST with CSRF token"]
    UNLINKBTN["Account Settings: Unlink Google button, POST"]
  end

  subgraph START["Start a flow"]
    STARTLOGIN["GET /auth/google/start with intent login and next query parameter"]
    STARTSET["POST /settings/google/link, user must be signed in"]
    SETQ{"User already has a Google account?"}
    SETALREADY["Back to settings: already linked, no flow started"]
    MKFLOW["Store flow record in Redis key goidc:state, TTL 600 s<br/>holds state, nonce, PKCE verifier, intent, user_id, origin page, next<br/>Set cookie goidc_state, HttpOnly Secure SameSite Lax, Max-Age 600"]
    REDISFAIL["Error page, no redirect to Google. Nothing changes"]
    TOGOOGLE["Redirect to Google authorize URL<br/>scope openid email profile, PKCE S256, state, nonce"]
  end

  CONSENT["Google consent screen"]

  subgraph CALLBACK["Callback"]
    CB["GET /auth/google/callback with state and code or error"]
    STATEQ{"Flow record exists for state and cookie matches? Consume with GETDEL"}
    BADSTATE["Error page: sign-in link is invalid or has expired. Nothing changes, existing session kept"]
    ERRQ{"Google returned an error?"}
    NEUTRAL["Redirect to origin page with neutral message: Google sign-in was not completed"]
    EXCH["Exchange code at Google token endpoint with PKCE verifier<br/>Validate ID token: signature, iss, aud, exp, nonce<br/>Read only sub, email, email_verified"]
    EXCHFAIL["Error page: Google sign-in failed, try again. Nothing created, no pending link. Code is not retried"]
  end

  INTENTQ{"Intent?"}

  subgraph SETLINK["Settings link"]
    SESSQ{"sid cookie still belongs to flow user_id?"}
    LQ1{"sub already in google_identities?"}
    LSAME["Back to settings: already linked to this user"]
    LREFUSE1["Back to settings: refuse, this Google account belongs to another user"]
    LQ2{"This user already has a different Google account?"}
    LREFUSE2["Back to settings: refuse, unlink the current Google account first"]
    LINS["INSERT google_identities sub, user_id. Email not compared, stored email unchanged"]
    LCONFLICT["Back to settings: refuse, changed meanwhile"]
    LDONE["Back to settings: Google linked"]
  end

  subgraph LOGINPATH["Login path"]
    LQ0{"sub already linked to a user?"}
    LOCKQ1{"Linked user locked_until in the future?"}
    LLOCKED["Login page: Account temporarily locked"]
    VERQ{"email_verified is true?"}
    REFUNVER["Login page: Google email not verified, use email and password. Nothing created"]
    EMQ{"Lowercased email matches a users row?"}
    CREATE["INSERT users: lowercased email, password_hash NULL, email_verified_at now<br/>INSERT google_identities for the new user"]
    HASQ{"That user already has a google_identities row?"}
    REFOTHER["Login page: refuse, this account already has a different Google account"]
    PEND["Create pending link in Redis key glink token, TTL 600 s, holds sub, user_id, next<br/>Set cookie glink, same attributes<br/>Redirect to confirm page"]
  end

  subgraph CONFIRM["Password confirmation loop, 10 minutes from callback"]
    PFORM["Confirm page: ask for the account password"]
    PPOST["POST password"]
    PQ{"Pending link found for glink cookie?"}
    PEXP["Login page: sign-in expired, start again"]
    PLOCKQ{"locked_until in the future?"}
    PLOCKED["Delete pending link. Login page: Account temporarily locked. Password not checked"]
    PCHK{"bcrypt password matches?"}
    PFAIL["failed_logins plus 1"]
    PFIVE{"failed_logins reached 5?"}
    PWRONG["Show incorrect password. Pending link kept"]
    PLOCKSET["Set locked_until to now plus 15 min, failed_logins to 0. Delete pending link. Respond as existing wrong-password path"]
    PINS{"INSERT google_identities succeeds?"}
    PCONFLICT["Delete pending link. Login page: refuse, changed meanwhile"]
    POK["failed_logins 0. Set email_verified_at if NULL. Delete pending link"]
    PCANCEL["Delete pending link. Login page"]
  end

  SIGNIN["start_session user_id, same as password login: delete old sid row if sent, insert sessions row, set sid cookie, redirect to next or /home"]

  LOGIN --> STARTLOGIN
  SETTINGS --> STARTSET
  STARTLOGIN --> MKFLOW
  STARTSET --> SETQ
  SETQ -- "yes" --> SETALREADY
  SETQ -- "no" --> MKFLOW
  MKFLOW -- "Redis write fails" --> REDISFAIL
  MKFLOW -- "ok" --> TOGOOGLE
  TOGOOGLE --> CONSENT
  CONSENT -- "user approves" --> CB
  CONSENT -- "user presses Cancel" --> CB
  CB --> STATEQ
  STATEQ -- "no: unknown, expired, used, or cookie mismatch" --> BADSTATE
  STATEQ -- "yes" --> ERRQ
  ERRQ -- "yes" --> NEUTRAL
  ERRQ -- "no" --> EXCH
  EXCH -- "network error, non-2xx, or invalid ID token" --> EXCHFAIL
  EXCH -- "valid" --> INTENTQ
  INTENTQ -- "settings" --> SESSQ
  INTENTQ -- "login" --> LQ0
  SESSQ -- "no" --> BADSTATE
  SESSQ -- "yes" --> LQ1
  LQ1 -- "to this user" --> LSAME
  LQ1 -- "to another user" --> LREFUSE1
  LQ1 -- "not linked" --> LQ2
  LQ2 -- "yes" --> LREFUSE2
  LQ2 -- "no" --> LINS
  LINS -- "unique violation" --> LCONFLICT
  LINS -- "ok" --> LDONE
  LQ0 -- "yes" --> LOCKQ1
  LQ0 -- "no" --> VERQ
  LOCKQ1 -- "yes" --> LLOCKED
  LOCKQ1 -- "no" --> SIGNIN
  VERQ -- "no" --> REFUNVER
  VERQ -- "yes" --> EMQ
  EMQ -- "no" --> CREATE
  EMQ -- "yes" --> HASQ
  CREATE -- "unique violation on email, retry check once" --> EMQ
  CREATE --> SIGNIN
  HASQ -- "yes" --> REFOTHER
  HASQ -- "no" --> PEND
  PEND --> PFORM
  PFORM --> PPOST
  PPOST --> PQ
  PQ -- "no" --> PEXP
  PQ -- "yes" --> PLOCKQ
  PLOCKQ -- "yes" --> PLOCKED
  PLOCKQ -- "no" --> PCHK
  PCHK -- "no" --> PFAIL
  PFAIL --> PFIVE
  PFIVE -- "no" --> PWRONG
  PWRONG --> PFORM
  PFIVE -- "yes" --> PLOCKSET
  PCHK -- "yes" --> PINS
  PINS -- "unique violation" --> PCONFLICT
  PINS -- "ok" --> POK
  POK --> SIGNIN
  PFORM -- "Cancel" --> PCANCEL
  UNLINKBTN --> UQ{"users.password_hash set?"}
  UQ -- "no" --> UNOPW["Settings: set a password first, use Forgot password to get a reset email"]
  UQ -- "yes" --> UDEL["Delete google_identities row for this user. Back to settings: Google unlinked"]
```

## Where new state lives

| State | Where | Lifetime | What removes it |
|---|---|---|---|
| Flow record: state, nonce, PKCE verifier, intent, user_id (settings only), origin page, next | Redis key `goidc:<state>` | 600 s from start | GETDEL at the first callback, whatever the outcome, or TTL expiry |
| Flow cookie `goidc_state` | Browser, HttpOnly, Secure, SameSite=Lax (Lax so it is sent on Google's top-level redirect) | 600 s | Cleared on the callback response, or expiry |
| Pending link: sub, user_id, next | Redis key `glink:<token>` | 600 s from the callback that created it | Success, Cancel, lock, or TTL. A wrong password keeps it |
| Pending cookie `glink` | Browser, same attributes | 600 s | Cleared with the pending link |
| Google account link | Postgres `google_identities` (new, permanent) | Permanent | Unlink (only with a password), or user deletion (cascade). A Google email change never removes it |
| Google-created user | Postgres `users`, password_hash NULL | Permanent | User deletion |
| Lockout | `users.failed_logins`, `locked_until` (existing) | Existing rules | Lock expiry. A successful password check resets failed_logins |
| Session | `sessions` row and `sid` cookie (existing) | 14 days, slid | Sign-out, password reset, or replacement by start_session |
| Google access token, refresh token, raw ID token | Not stored | In memory during the callback only | Discarded once the three claims are read |

Redis holds only short-lived flow data. If Redis is down, Google sign-in fails with an error page, and password login still works.

## Failures

| Failure | Result | Changes made |
|---|---|---|
| Unknown, expired, used, or cookie-mismatched state | Error page: sign-in link invalid or expired | None. Existing session kept |
| Redis unavailable at start | Error page, no redirect to Google | None |
| Redis unavailable at callback | Error page | None. The flow expires by TTL |
| Google error parameter, e.g. Cancel | Back to origin page with neutral message | Flow record consumed |
| Settings callback where sid no longer belongs to flow user_id | Error page | Flow record consumed |
| Code exchange fails: network error, non-2xx, bad signature, or bad iss, aud, exp or nonce | Error page: Google sign-in failed, try again | Nothing created, no pending link. The code is not retried, so the user starts a new flow |
| Unlinked sub with email_verified false | Refuse, point to email and password | Nothing created |
| Verified email matches a user who already has another Google account | Refuse | Nothing created |
| Settings link where sub belongs to another user | Refuse | None |
| Settings link where this user already has a different Google account | Refuse, unlink first | None |
| Unique violation on user create (email race) | Repeat the email check once. If still conflicting, error page | Failed attempt rolled back |
| Unique violation on link insert | Refuse | Transaction rolled back |
| Pending link expired | Login page: sign-in expired, start again | Pending link gone by TTL |
| Wrong password, not yet 5 | Show incorrect password, stay on form | failed_logins plus 1. Pending link kept |
| Fifth wrong password | Respond as the existing wrong-password path. Next attempt gets Account temporarily locked | locked_until set 15 min, failed_logins 0, pending link deleted |
| Account locked at confirm | Account temporarily locked. Password not checked | Pending link deleted |
| Cancel at confirm | Back to login | Pending link deleted |
| Unlink without a password | Set a password first, using Forgot password | None |
| Unlink with a password | Google unlinked | google_identities row deleted |

Forgot password sets a password_hash and deletes all sessions, so the user signs in again afterwards.

## Schema change

```sql
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

CREATE TABLE google_identities (
  sub       TEXT PRIMARY KEY,                    -- Google account id from the ID token
  user_id   BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  linked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

The primary key on `sub` gives one user per Google account. The unique `user_id` gives one Google account per user. Both are enforced by the database, so races surface as unique violations. Any code that compares against `password_hash` must handle NULL. A password attempt on a NULL-hash account should get the same response as a wrong password and count as a failure, so the response does not reveal whether the account has a password.

## Decisions to confirm

The brief does not settle these. Defaults are given.

1. **Locked account, Google sign-in.** A linked user with a future `locked_until` is refused with Account temporarily locked. Google sign-in skips the password, but the lock is an account state. Default: honour it.
2. **Session holder links Google.** Settings linking needs no password, so someone holding a live session could link their own Google account and sign in as the user later. The brief allows this. Consider a recent-login check before linking.
3. **email_verified_at on link.** When linking an existing user through the password step, set `email_verified_at` if it is NULL, since Google has verified the email. Default: yes.
4. **Failed-login count on Google sign-in.** Google-only sign-in does not change `failed_logins`. Only the password step resets it. Default: no change.
5. **CSRF.** The existing docs do not mention a CSRF token. The link and unlink POSTs assume the app has one.
6. **Restarted flow.** A second callback replaces the `glink` cookie and pending record. The old pending record expires on its own. Default: accept this.
7. **Settings entry while signed out.** The settings link should redirect to login. The flow is not started.