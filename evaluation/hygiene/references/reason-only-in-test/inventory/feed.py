"""Read stock updates from the warehouse feed."""


def latest_updates(updates):
    """Return the update to apply for each SKU.

    The last update for a SKU wins: the warehouse corrects a miscount by sending the
    SKU again later in the feed.
    """
    latest = {}
    for update in updates:
        latest[update["sku"]] = update
    return list(latest.values())


def total_units(updates):
    """Return the units in stock across every SKU."""
    return sum(update["count"] for update in latest_updates(updates))
