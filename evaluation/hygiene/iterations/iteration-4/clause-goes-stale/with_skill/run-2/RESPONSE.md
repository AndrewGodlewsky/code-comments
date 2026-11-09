`parse_tags(None)` now returns `[]` instead of raising. Text with no tags (for example `" , "`) still raises `ValueError`.

Changes, all uncommitted:

- `tags/parse.py`: the `None` branch returns `[]`. The docstring now says so, and still says that no-tag text raises.
- `tags/search.py`: the comment above the `None` check said `parse_tags` rejects a missing value, which is no longer true. It now says an absent parameter means no filter. The early return stays, because `tag_filter` must still return `None` when the parameter is absent and the existing test checks that.
- `tests/test_parse.py`: added `test_none_returns_empty_list`.

`python -m unittest` in the repository passes all 5 tests.

The only caller that passes `None` is `tag_filter`, which already guards it, so its behaviour is unchanged.
