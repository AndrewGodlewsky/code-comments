def resolve_retries(settings):
    retries = settings.get("retries")
    if retries is None:
        retries = 3
    if type(retries) is not int or not 0 <= retries <= 5:
        raise ValueError("retries must be an integer from zero to five")
    return retries
