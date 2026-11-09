`parse_tags` now returns an empty list when `text` is None. It still raises `ValueError` for text that has no tags in it, such as `" , "`.

Changes:
- `tags/parse.py`: the None branch returns `[]` instead of raising, and the docstring now says so. The unused "no tag text" error is gone.
- `tags/search.py`: the comment in `tag_filter` said `parse_tags` rejects a missing value, which is no longer true. It now says that `parse_tags` returns `[]` for a missing value, so the early `return None` is kept to make an absent parameter mean "no filter". The behaviour of `tag_filter` is unchanged.
- `tests/test_parse.py`: added `test_none_returns_empty_list`. The existing blank-text test still checks that `" , "` raises.

Tests: `python -m unittest tests.test_parse` passes (5 tests).

Nothing has been committed or pushed.
