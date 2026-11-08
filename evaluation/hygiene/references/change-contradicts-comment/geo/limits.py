"""Rate limits for calls to the Geoway geocoding API."""

# Geoway's free tier allows 100 requests a minute per API key. Going over returns
# HTTP 429 for the rest of that minute, so keep this at or below the quota.
REQUESTS_PER_MINUTE = 250
