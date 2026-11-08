`parse_tags(None)` now returns `[]` instead of raising `ValueError`. Text with no tags (for example `" , "` or `""`) still raises `ValueError`.

Changes:

- `tags/parse.py`: `None` returns `[]`. The docstring now says so, and still states that non-None text with no tags raises.
- `tags/search.py`: the comment above the `None` check said `parse_tags` rejects a missing value. That is no longer true, so I reworded it. The early return is kept because an absent parameter means "no tag filter", which is different from an empty tag list.
- `tests/test_parse.py`: added `test_none_gives_no_tags`.

`python -m unittest` passes all 5 tests.

Nothing is committed.
