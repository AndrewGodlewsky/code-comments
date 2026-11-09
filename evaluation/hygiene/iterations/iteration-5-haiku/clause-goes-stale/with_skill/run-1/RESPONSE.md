`parse_tags(None)` now returns `[]` instead of raising. Text with no tags in it (for example `" , "`) still raises `ValueError`.

Changes, all uncommitted:

- `tags/parse.py`: the `None` branch returns `[]`. The docstring now says so and still says that blank text raises.
- `tags/search.py`: `tag_filter` keeps its early `return None` for a missing `tags` parameter, because `None` means "no filter" and `[]` would mean "filter on no tags". I rewrote its comment, which said `parse_tags` rejects a missing value and is no longer true.
- `tests/test_parse.py`: added `test_none_text_returns_empty_list`. The existing blank-text test still covers the raise.

Tests: `python -m unittest discover -s tests -t .` runs 5 tests, all passing.

I did not commit anything. Nothing was run against git, and this directory is not a git repository.
