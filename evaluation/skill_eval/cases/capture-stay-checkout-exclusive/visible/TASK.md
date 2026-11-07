# Build the partner availability request

We're wiring the booking form up to the partner's availability endpoint. Add
`availability_query(hotel_id, first_night, last_night)` to `stays.py`. It takes
the stay as the booking form models it (a `date` for the first and the last
night) and returns the JSON body for `POST /availability` as a dict with
`hotel_id`, `checkin` and `checkout`.

Raise `ValueError` for anything the partner would reject, so we fail before the
network call. The partner's API notes are in `docs/partner-api.md`.
