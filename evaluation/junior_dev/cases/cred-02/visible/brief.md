## Two-factor sign-in with an authenticator app

We're adding optional TOTP two-factor authentication (Google Authenticator, 1Password and similar apps) to our existing email-and-password login. Read `existing/login.py` and `existing/schema.sql` first. They show how sign-in, sessions and the `sid` cookie work today, and which helpers already exist (`seal`/`unseal`, `enqueue_email`, `start_session`). Reuse them and keep the current session mechanism.

**Fixed requirements**

- Users turn 2FA on themselves from Security settings while signed in. The server generates a secret and shows a QR code. Sign-in ignores the new secret until the user types a valid code from their app. Only then is 2FA on.
- Codes follow RFC 6238: 6 digits, 30-second steps, accepting one step either side of the server's clock. If a code's time step has already been accepted for that user, the code must be rejected.
- Secrets are stored encrypted with `seal()`. Recovery codes are stored only as hashes.
- Every time an authenticator is confirmed (first setup or a replacement), the user gets 10 new single-use recovery codes. They are shown once and never again, and all previous codes stop working. When 2FA is confirmed, every other session of that user is signed out. The current session stays.
- Sign-in: the password check stays as it is. For a user with 2FA on, a correct password must not create a session. The user must then enter an authenticator code or an unused recovery code. This in-between step lasts at most 5 minutes and allows 5 wrong entries. When either limit is reached, the step is thrown away and the user starts again from the password.
- Using a recovery code signs the user in, uses up that code, and emails the user to say a code was used and how many remain. Sign-in must not wait for the email.
- Lost phone: a user who signs in with a recovery code must be able to set up a new authenticator straight away.
- Turning 2FA off requires the password and a valid authenticator or recovery code. It deletes the secret and all recovery codes.

**Not decided**

Product has not decided yet what happens to a user who has lost their phone and has no unused recovery codes (for example, whether support may reset 2FA, and how they would check the person's identity). Don't design that path. Mark it as open.

**What I want**

A Mermaid `stateDiagram-v2` covering the account's 2FA lifecycle and a single sign-in attempt, with short notes before or after it. The notes should say where each piece of new state lives, what triggers each transition, and what happens on failure.
