`parse_tags(None)` now returns `[]` instead of raising `ValueError`. Text that is a string but holds no tags (for example `" , "`) still raises `ValueError`, as before.

Changes:
- `tags/parse.py`: the `None` check returns `[]`, and the docstring describes the new behaviour.
- `tags/search.py`: the only caller that passes `None` is `tag_filter`. It already returns `None` early when the `tags` parameter is absent, so its behaviour is unchanged. I only rewrote the comment, which said `parse_tags` rejects a missing value and is no longer true.
- `tests/test_parse.py`: added `test_none_returns_empty_list`.

All 5 tests pass (`python -m unittest discover -s tests -t .`).
