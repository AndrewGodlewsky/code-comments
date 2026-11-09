"""Push invoices to the payment API."""
from ledger.client import fetch_with_retry

# Kept small so that one failed batch does not hold up the rest.
BATCH_LIMIT = 20


def batches(invoices):
    """Yield the invoices in batches of at most BATCH_LIMIT."""
    for start in range(0, len(invoices), BATCH_LIMIT):
        yield invoices[start:start + BATCH_LIMIT]


def push(invoices, endpoint):
    """Send every batch to endpoint and return the batches that failed."""
    failed = []
    for batch in batches(invoices):
        # fetch_with_retry makes up to 5 attempts before giving up.
        ids = ",".join(str(invoice.id) for invoice in batch)
        if fetch_with_retry(f"{endpoint}?ids={ids}") is None:
            failed.append(batch)
    return failed
