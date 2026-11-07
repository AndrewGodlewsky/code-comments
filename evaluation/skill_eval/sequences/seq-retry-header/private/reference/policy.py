# SPDX-License-Identifier: MIT


def resolve_retries(settings, override=None):
    # An override of None means "use settings"; an explicit zero must still win,
    # so test for None rather than truthiness.
    retries = settings.get("retries") if override is None else override
    if retries is None:
        retries = 3
    # The upgraded backend accepts at most eight retries and rejects larger values.
    if type(retries) is not int or not 0 <= retries <= 8:
        raise ValueError("retries must be an integer from zero to eight")
    return retries


def retries_for_request(settings, headers):
    """Resolve retries for one request, honouring the client's X-Retries header."""
    value = headers.get("X-Retries")
    if value is None:
        return resolve_retries(settings)
    # Parse only; resolve_retries owns the range and type rules, so the header
    # can never allow more than the backend accepts.
    try:
        override = int(value)
    except ValueError:
        raise ValueError(f"X-Retries must be a whole number: {value!r}") from None
    return resolve_retries(settings, override)
