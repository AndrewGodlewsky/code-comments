"""Read stock updates from the warehouse feed."""


def latest_updates(updates):
    """Return the update to apply for each SKU."""
    seen = {}
    for update in reversed(updates):
        sku = update["sku"]
        if sku not in seen:
            seen[sku] = update
    return list(reversed(list(seen.values())))


def total_units(updates):
    """Return the units in stock across every SKU."""
    return sum(update["count"] for update in latest_updates(updates))
