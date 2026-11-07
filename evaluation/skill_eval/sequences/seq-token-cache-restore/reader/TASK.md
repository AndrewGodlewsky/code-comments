# Don't crash on tokens restored from old caches

The desktop app saves the token response to disk between launches. Before
build 4.2 the cache serializer only wrote `access_token`, `token_type` and
`issued_at`, so a user upgrading from 4.1 or earlier restores a token with no
`expires_at`. `needs_refresh` raises `KeyError` on those tokens and the app
shows its crash screen on launch.

Make `needs_refresh` handle a stored token that has no `expires_at`. Tokens
that do have `expires_at` must behave exactly as they do now.
