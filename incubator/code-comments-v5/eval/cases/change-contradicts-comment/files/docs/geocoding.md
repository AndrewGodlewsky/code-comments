# Geocoding

Addresses are geocoded through Geoway. The client sends at most 100 requests a
minute, spaced evenly.

Failed lookups are logged and retried in the next nightly run.
