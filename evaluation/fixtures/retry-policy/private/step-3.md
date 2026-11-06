# Add bounded retry delays

Add `retry_delays(settings, override=None)` in `policy.py`. Resolve the count
using the existing policy and return a list of seconds, one per retry. Start at
one second, double each time, and cap each delay at four seconds to bound recovery
latency. For five retries return `[1, 2, 4, 4, 4]`; zero returns `[]`. Do not add
a delay for the initial operation. Propagate invalid-count ValueError and retain
all existing resolution behavior.
