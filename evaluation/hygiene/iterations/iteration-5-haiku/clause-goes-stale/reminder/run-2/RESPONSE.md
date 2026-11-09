`parse_tags(None)` now returns `[]` instead of raising. Blank or comma-only text such as `" , "` still raises `ValueError`, as before.

Changes:
- `tags/parse.py`: the `None` branch returns `[]`, and the docstring now says so. It still says that text with no tags raises.
- `tags/search.py`: the comment above the early return said `parse_tags` rejects a missing value, which is no longer true. It now says that a missing parameter must stay `None` (no filter), which the empty list would hide. The early return is kept, so `tag_filter({})` still returns `None`.
- `tests/test_parse.py`: added `test_none_returns_empty_list`.

Tests: all 5 pass (`python -m unittest discover -s tests -t .`).
