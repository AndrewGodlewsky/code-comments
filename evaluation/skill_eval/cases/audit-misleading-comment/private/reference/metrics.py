import time


# Not thread-safe, and there is no lock: since 2.0 every call comes from the
# event-loop thread.
class RequestStats:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.count = 0
        self.errors = 0
        self.started = clock()

    def record(self, ok):
        self.count += 1
        if not ok:
            self.errors += 1

    def error_rate(self):
        # Report 0.0 instead of dividing by zero before the first request: the
        # health endpoint polls this immediately at startup.
        if self.count == 0:
            return 0.0
        return self.errors / self.count

    def per_second(self):
        elapsed = max(self.clock() - self.started, 1e-9)
        return self.count / elapsed
