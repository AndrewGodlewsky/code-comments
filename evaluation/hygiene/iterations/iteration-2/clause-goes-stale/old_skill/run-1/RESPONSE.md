`parse_tags(None)` now returns `[]` instead of raising. Text with no tags, such as `" , "`, still raises `ValueError`.

Changes:
- `tags/parse.py`: the `None` branch returns `[]`, and the docstring now says so.
- `tags/search.py`: the comment in `tag_filter` said `parse_tags` rejects a missing value, which is no longer true. It now says that an absent parameter means no filter, which differs from the empty list. The early `return None` is kept, so `tag_filter({})` still returns `None`.
- `tests/test_parse.py`: added `test_none_returns_empty_list`.

Tests: all 5 pass (`python -m unittest discover -s tests -t .`).
