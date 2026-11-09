"""HTTP client for the billing service."""
import time
import urllib.request


# The billing service drops connections during its nightly failover, so a
# failed request is retried with exponential backoff.
def fetch_with_retry(url, attempts=3, delay=0.5):
    """Return the response body for url, or None if every attempt fails."""
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read()
        except OSError:
            time.sleep(delay * 2 ** attempt)
    return None
