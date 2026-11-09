`parse_tags(None)` now returns `[]` instead of raising. Text that is not None but contains no tags, such as `" , "`, still raises `ValueError`.

Changes:

- `tags/parse.py`: the `None` branch returns an empty list, and the docstring describes the new behaviour.
- `tags/search.py`: I kept the early return in `tag_filter`, because an absent `tags` parameter should still mean "no filter" (`None`), which is different from an empty tag list. The comment said `parse_tags` rejects a missing value, which is no longer true, so I rewrote it.
- `tests/test_parse.py`: added `test_none_returns_empty_list`. The existing blank-text test still checks that `" , "` raises.

All 5 tests pass (`python -m unittest discover -s tests -t .`). I did not commit anything.
