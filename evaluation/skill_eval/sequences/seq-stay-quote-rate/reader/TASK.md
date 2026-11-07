# Show the nightly rate from partner quotes

The partner's `POST /availability` now answers with a quote. The response body
is a dict like this:

```python
{"hotel_id": "H-17", "checkin": "2026-05-04", "checkout": "2026-05-09", "total_cents": 61000}
```

`checkin` and `checkout` are ISO dates (`YYYY-MM-DD`) in the partner's usual
format, and `total_cents` is the price of the whole stay.

The results page shows a price per night. Add `nightly_rate(quote)` to
`stays.py`: it returns the average price per night of the quoted stay, in whole
cents, rounded down. Raise `ValueError` if the quote's dates don't describe a
stay of at least one night, so a malformed quote never reaches the page.

Keep `availability_query` and `nights` working as they do today.
