"""Translate stays from the booking form into partner API requests."""

from datetime import timedelta

PARTNER_MAX_NIGHTS = 30


def nights(first_night, last_night):
    """Number of nights in a stay; both dates are nights the guest sleeps there."""
    if last_night < first_night:
        raise ValueError("last night is before the first night")
    return (last_night - first_night).days + 1


def availability_query(hotel_id, first_night, last_night):
    count = nights(first_night, last_night)
    if count > PARTNER_MAX_NIGHTS:
        raise ValueError(f"the partner accepts at most {PARTNER_MAX_NIGHTS} nights, got {count}")
    # Our last night is inclusive (the guest sleeps there), but the partner's
    # checkout is exclusive: the morning the guest leaves, which is not charged.
    checkout = last_night + timedelta(days=1)
    return {"hotel_id": hotel_id, "checkin": first_night.isoformat(), "checkout": checkout.isoformat()}
