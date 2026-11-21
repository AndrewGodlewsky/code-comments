## Personal API tokens on the Account Settings page

**Goal.** Signed-in users need personal API tokens so their scripts and CI jobs can call our REST API without using a password. Everything happens on the existing Account Settings page. It is backed by our single web/API server and its Postgres database.

**Fixed requirements**

- **Create.** The user enters a name of 1 to 40 characters. The name must be unique among that user's active tokens. The server generates the token: `pat_` followed by 32 characters from a cryptographically secure random source. The full token is shown exactly once, in the response to the create request, with a Copy button. Once the user closes that dialog nobody can show the token again, including support and engineering. A user who loses a token has to create a new one.
- **Never store the plaintext.** Store a SHA-256 hash of the token. The plaintext must never appear in the database, the logs or analytics.
- **Expiry.** Every token expires 90 days after it is created and cannot be renewed.
- **Limit.** A user may have at most 10 active tokens. Active means not revoked and not expired. If a user tries to create an 11th, the request is refused and the message tells them to revoke a token first.
- **List.** The page lists every active token with its name, created date, expiry date and last-used time. A token that has never been used shows "Never". The last-used time may be up to 1 hour out of date. We do not want a database write on every API request.
- **Revoke.** The user clicks Revoke and confirms. The very next API request that uses the token must be rejected with 401. Do not cache token validity in any way that would delay this.
- **Using a token.** API clients send `Authorization: Bearer <token>`. A missing, unknown, revoked or expired token gets a 401 with the same generic body in every case, so the response does not reveal which one it was.
- Users can see and revoke only their own tokens.

**Existing system.** Session-cookie login already works, and the settings endpoints already sit behind it. There is no token table yet.

**Deliverable.** A Mermaid `sequenceDiagram` with short notes before or after it. It should cover four flows: creating a token, listing tokens, an API call authenticated by a token (including how the last-used time gets recorded), and revoking a token. Show where each piece of state lives. Show what happens on failures, including the limit being reached, a bad token, and a create response that never reaches the browser.
