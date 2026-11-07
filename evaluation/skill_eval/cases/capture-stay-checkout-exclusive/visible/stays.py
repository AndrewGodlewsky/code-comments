"""Translate stays from the booking form into partner API requests."""


def nights(first_night, last_night):
    """Number of nights in a stay; both dates are nights the guest sleeps there."""
    if last_night < first_night:
        raise ValueError("last night is before the first night")
    return (last_night - first_night).days + 1
