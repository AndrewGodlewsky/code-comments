def resolve_retries(settings, override=None):
    retries = settings.get("retries") if override is None else override
    if retries is None:
        retries = 3
    if type(retries) is not int or not 0 <= retries <= 8:
        raise ValueError("retries must be an integer from zero to eight")
    return retries


def retry_delays(settings, override=None):
    count = resolve_retries(settings, override)
    return [min(2 ** index, 4) for index in range(count)]
