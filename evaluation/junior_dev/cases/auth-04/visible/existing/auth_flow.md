# How sign-in works today

One backend service renders the pages (no SPA, no mobile app). PostgreSQL holds
the tables in schema.sql. Redis is available and is used today only for
short-lived data such as rate limits.

## Password sign-in: POST /login

1. Lowercase the submitted email and load the user.
2. If locked_until is in the future, reject with: Account temporarily locked.
   The password is not checked.
3. Compare the password with bcrypt.
   - Wrong: failed_logins + 1. When it reaches 5, set locked_until to
     now + 15 minutes and set failed_logins back to 0.
   - Right: set failed_logins to 0, then call start_session.
4. Unknown email and wrong password show the same generic message.

## start_session(user_id)

- If the browser already sent a sid cookie, delete that sessions row first.
- Insert a sessions row and set cookie sid (HttpOnly, Secure, SameSite=Lax).
- Redirect to the next query parameter if it is a relative path on our site,
  otherwise to /home.

## Sign-out

Delete the sessions row and clear the sid cookie.

## Password reset

POST /forgot emails a link valid for one hour. Using it sets a new
password_hash, marks the email verified, and deletes all of the user's sessions.
