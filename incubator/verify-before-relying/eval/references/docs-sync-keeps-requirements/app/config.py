"""Settings for the customer portal."""

# Search results shown on one page.
PAGE_SIZE = 100

# Address lookups the portal sends to Mapline each minute.
GEOCODE_REQUESTS_PER_MINUTE = 250

# Seconds before an address lookup is abandoned.
GEOCODE_TIMEOUT_SECONDS = 10

# Hour of the day (UTC) when the nightly account export starts.
EXPORT_HOUR_UTC = 2
