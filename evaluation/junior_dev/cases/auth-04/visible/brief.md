## Add "Sign in with Google" beside email and password

We're adding Google sign-in (OpenID Connect) to our server-rendered web app. The current tables and login behaviour are in `existing/schema.sql` and `existing/auth_flow.md`. Build on them; don't replace them.

**Fixed requirements**

- Use the authorization-code flow with PKCE, a `state` and a `nonce`, with scopes `openid email profile`. We do not keep Google access or refresh tokens. At sign-in we read only the ID token's `sub`, `email` and `email_verified`.
- The round trip to Google must finish within 10 minutes, and we honour each attempt's callback once. A callback with an unknown, expired or already-used `state` gets an error page and changes nothing. If Google sends back an error (for example, the user pressed Cancel), return the user to where they started with a neutral message.
- We identify a Google account by `sub`, never by email. A Google account links to at most one of our users, and a user has at most one Google account. If a linked user's Google email changes, they still reach the same account. Google never changes our stored email.
- Unlinked `sub` with `email_verified` false: refuse and point the user to email and password. Nothing is created.
- Unlinked `sub` with a verified email that matches no user: create a user with no password and a verified email, link it and sign in.
- Unlinked `sub` with a verified email that matches an existing user: don't sign in yet. Ask for that account's password, and if it is correct, link and sign in. Wrong passwords go through the existing lockout rules. If the account locks, throw away the half-finished link. The user has 10 minutes to confirm. If that account already has a different Google account linked, refuse.
- Signed-in users can also link Google from Account Settings. No password is asked there and the emails need not match. Refuse if that Google account is already linked to someone else.
- Users may unlink Google only if they have a password. Otherwise, tell them to set one with the existing reset email.
- Every successful Google sign-in ends in exactly the same session as a password login. No new session type.

**Deliverable**

A **Mermaid flowchart** with short notes before or after it. It must cover both entry points (login page and settings), every callback outcome and the password-confirmation loop. Say where each new piece of state lives, temporary and permanent, and what removes it. Say what happens on each failure, including a failed code exchange with Google. Write it for an engineer who has not seen the existing files.
