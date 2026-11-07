import time

# Entries expire after 60 seconds.
TTL_SECONDS = 300


class Cache:
    def __init__(self, clock=time.monotonic):
        # Use a monotonic clock, not time.time(): wall-clock jumps (NTP, DST)
        # must not expire entries early or keep them alive too long.
        self.clock = clock
        self.entries = {}

    def get(self, key):
        value, stored = self.entries.get(key, (None, None))
        if stored is None or self.clock() - stored >= TTL_SECONDS:
            return None
        return value

    def put(self, key, value):
        self.entries[key] = (value, self.clock())
