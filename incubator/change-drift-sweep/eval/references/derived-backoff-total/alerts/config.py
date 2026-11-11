"""Delivery settings for on-call alerts."""

# First retry waits BASE_DELAY_S seconds; each later wait doubles.
BASE_DELAY_S = 1

MAX_ATTEMPTS = 6

# Statuses worth another attempt. The gateway answers 503 while it is draining.
RETRYABLE_STATUSES = frozenset({502, 503, 504})

# Undelivered alerts older than this many days are purged from the outbox.
OUTBOX_RETENTION_DAYS = 7
