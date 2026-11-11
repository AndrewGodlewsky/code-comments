# Security model

## Sessions

Idle sessions end after 15 min; the user must sign in again.
Every request restarts the idle timer.

Access tokens from the company identity provider last 15 minutes.
The identity team sets that lifetime, not this service.

## Passwords

Password-reset links expire after 15 minutes.
An account is locked after 15 failed sign-ins in a row; an admin unlocks it from the user page.
