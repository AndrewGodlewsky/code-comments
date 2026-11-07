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
