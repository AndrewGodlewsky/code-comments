"""Settings for the notification batcher."""

# Most notifications sent in one call to the push provider.
BATCH_SIZE = 100

# Seconds a partial batch may wait before it is sent anyway.
FLUSH_INTERVAL_S = 30
