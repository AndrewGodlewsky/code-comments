"""Settings for the nightly order sync."""

# How far back each sync looks, in days.
ORDER_WINDOW_DAYS = 14

# Attempts per shop API request.
ATTEMPTS = 5

# Seconds to wait after the first failed attempt.
PAUSE_SECONDS = 2
