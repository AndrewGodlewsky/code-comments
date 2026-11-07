"""Decide when to refresh the OAuth access token held by the API client."""

REFRESH_MARGIN_S = 60


def needs_refresh(token, now):
    """Return True when ``token`` should be replaced before the next request.

    ``token`` is the issuer's token response as stored, or None; ``now`` is
    the current Unix time in seconds.
    """
    if token is None:
        return True
    # Tokens are valid for exactly one hour from issue; the issuer does not
    # send an expiry, so derive it from issued_at.
    expires_at = token["issued_at"] + 3600
    # Refresh a minute early: the gateway's clock can run up to a minute ahead
    # of ours, and it rejects tokens it already considers expired.
    return now >= expires_at - REFRESH_MARGIN_S
