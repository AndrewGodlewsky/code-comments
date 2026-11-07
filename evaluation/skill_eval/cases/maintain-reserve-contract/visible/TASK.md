# Make reserve fail loudly

Follow up on the review in `docs/review-88.md`: change `reserve` so a shortage
raises `InsufficientStock` (the batch importer already uses it) instead of
returning `False`, and so a successful call returns how many units of that SKU
are left. The checkout and re-order callers will be updated in a separate PR.
