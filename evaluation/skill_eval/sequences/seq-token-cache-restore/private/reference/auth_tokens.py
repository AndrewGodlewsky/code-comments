"""Decide when to refresh the OAuth access token held by the API client."""

REFRESH_MARGIN_S = 60


def needs_refresh(token, now):
    """Return True when ``token`` should be replaced before the next request.

    ``token`` is the issuer's token response as stored, or None; ``now`` is
    the current Unix time in seconds. Tokens restored from caches written
    before build 4.2 have no ``expires_at`` and are always refreshed.
    """
    if token is None:
        return True
    # Trust the issuer's expires_at: lifetimes are configured per client
    # (15 minutes to 12 hours), so no fixed lifetime can be assumed.
    expires_at = token.get("expires_at")
    if expires_at is None:
        # Pre-4.2 caches dropped expires_at. For the same reason it cannot be
        # rebuilt from issued_at plus a guessed lifetime, so refresh: one extra
        # round trip is cheaper than sending a token the gateway may reject.
        return True
    # Refresh a minute early: the gateway's clock can run up to a minute ahead
    # of ours, and it rejects tokens it already considers expired.
    return now >= expires_at - REFRESH_MARGIN_S
