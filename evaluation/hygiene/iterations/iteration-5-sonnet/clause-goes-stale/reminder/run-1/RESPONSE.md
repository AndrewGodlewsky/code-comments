`parse_tags(None)` now returns `[]`. Text with no tags in it, such as `" , "`, still raises `ValueError`.

Changes:
- `tags/parse.py`: the early return replaces the raise, and the docstring now says None gives an empty list and only non-None text with no tags raises.
- `tags/search.py`: the comment in `tag_filter` said parse_tags rejects a missing value, which is no longer true. I rewrote it to give the real reason for the early return: `tag_filter` keeps returning `None` for an absent parameter so callers can tell "no filter" from an empty one. Behaviour there is unchanged.
- `tests/test_parse.py`: added `test_none_returns_empty_list`.

The tests pass.
