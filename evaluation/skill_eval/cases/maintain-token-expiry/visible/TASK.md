# Use the issuer's token expiry

The token issuer changed its responses (see `docs/issuer-changelog.md`).
Update `needs_refresh` to work from what the issuer now sends. Everything we
have cached was issued after the change, so there are no old-format tokens to
handle.
