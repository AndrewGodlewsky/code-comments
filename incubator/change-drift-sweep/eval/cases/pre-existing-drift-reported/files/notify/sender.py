"""Hand batches to the push provider.

Each provider call carries one batch. The provider allows 20 calls a second per app, so
one app can push at most 2,000 notifications a second.
"""


def send_batch(provider, app, batch):
    """Send one batch for `app` in a single provider call."""
    provider.push(app=app, notifications=list(batch))
    return len(batch)
