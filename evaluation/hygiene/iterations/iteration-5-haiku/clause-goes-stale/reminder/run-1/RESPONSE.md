`parse_tags(None)` now returns `[]` instead of raising. Text with no tags in it (for example `" , "`) still raises `ValueError`.

Changes:
- `tags/parse.py`: the `None` check returns `[]`. The docstring now says so, and still says it raises for text with no tags.
- `tags/search.py`: the comment said `parse_tags` rejects a missing value, which is no longer true. The early return in `tag_filter` is still needed, because an absent parameter must mean "no filter" (`None`), not an empty filter (`[]`). The comment now says that.
- `tests/test_parse.py`: added `test_none_returns_empty_list`. The existing blank-text test still checks that `" , "` raises.

Tests: all 5 pass (`python -m unittest discover -s tests -t .`).

Nothing was committed.
