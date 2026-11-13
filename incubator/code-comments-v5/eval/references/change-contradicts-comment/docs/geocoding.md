# Geocoding

Addresses are geocoded through Geoway. The client sends at most 250 requests a
minute, spaced evenly.

Failed lookups are logged and retried in the next nightly run.
