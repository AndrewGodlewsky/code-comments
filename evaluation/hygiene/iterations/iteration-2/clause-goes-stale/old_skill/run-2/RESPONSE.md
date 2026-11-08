`parse_tags` now returns an empty list when `text` is `None`. It still raises `ValueError` when the text is present but holds no tags, such as `" , "`.

Changes:
- `tags/parse.py`: the `None` branch returns `[]`, and the docstring now describes both cases.
- `tags/search.py`: `tag_filter` still returns `None` for a missing `tags` parameter, so "no filter" stays distinct from "empty filter". The comment above that early return said `parse_tags` rejects a missing value, which is no longer true, so I rewrote it.
- `tests/test_parse.py`: added a test that `parse_tags(None)` returns `[]`.

The unit tests pass (5 of 5).
