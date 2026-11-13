## Login with server-side sessions

We're adding sign-in to our small team-scheduling app. Today every page is public. After this change, every page except `/login` needs a signed-in user. Before you build it, I want a design I can review.

**Existing system**
- Server-rendered web app: HTML pages and form posts, no SPA or API clients.
- It runs as two identical instances behind a load balancer, with no sticky sessions.
- One Postgres database, which already has a `users` table: `id`, `email` (stored lowercase, unique), `password_hash` (bcrypt). Sign-up and password reset are out of scope.

**Fixed requirements**
1. Login is `POST /login` with email and password. Emails are matched in lowercase.
2. An unknown email and a wrong password must get the identical response: HTTP 401 and the login page showing "Invalid email or password". Nothing may reveal whether an account exists.
3. Brute-force limit: once an email has 5 failed attempts within any 10-minute period, refuse logins for that email for 15 minutes with HTTP 429, without checking the password. A successful login clears that email's failure count.
4. On success, always issue a brand-new random session ID, even if the browser already sent one, and destroy whatever session the incoming cookie pointed to. Then redirect to `/dashboard`.
5. The cookie carries only the opaque session ID, flagged HttpOnly, Secure and SameSite=Lax. No user data goes in the cookie.
6. A session ends after 30 minutes with no requests (every request restarts that clock) or 12 hours after login, whichever comes first.
7. Every protected request checks the session on the server. If it is missing, unknown or expired, clear the cookie and redirect to `/login`.
8. Logout is `POST /logout`. Destroy the session on the server before replying, then clear the cookie and redirect to `/login`. It must behave the same when there is no session.

**Left to you**
These choices are yours: where sessions and failure counts live (process memory won't work with two instances, and Redis isn't in the stack today, so justify adding it), how expiry is checked and recorded, how abandoned sessions get removed, and what the user sees when storage fails. State each choice explicitly.

**Format**
A Mermaid `sequenceDiagram` covering login (success, bad credentials, lockout), a request for a protected page, and logout. Add short notes before or after the diagram for state and rules that don't fit on the arrows.
