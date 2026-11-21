## TOTP 2FA plan

New tables: `user_totp`, `recovery_codes`, `pending_logins`. New cookie `p2f`. Reuses `seal()`, `enqueue_email()` and `start_session()`.

```mermaid
stateDiagram-v2
    state "2FA off" as Off
    state "Setup pending" as SetupPending
    state "2FA on" as On
    state "Replacement pending" as ReplacePending
    state "Password" as Password
    state "Awaiting code" as Awaiting
    state "Signed in" as SignedIn

    [*] --> Off
    Off --> SetupPending
    SetupPending --> On
    On --> ReplacePending
    ReplacePending --> On
    On --> Off

    [*] --> Password
    Password --> SignedIn
    Password --> Awaiting
    Awaiting --> SignedIn
    Awaiting --> Password
```

Notes:
- Codes are 6-digit TOTP with drift tolerance and replay protection.
- Recovery codes: 10, single use, hashed, regenerated on confirm.
- Attempts are limited and pending logins expire.
- Lost phone: use a recovery code, then set up a new authenticator.
- The user gets an email when a recovery code is used.
- Other sessions are handled when 2FA is enabled.
- Disable needs re-authentication.
- Support reset for users with no phone and no codes: TBD.
