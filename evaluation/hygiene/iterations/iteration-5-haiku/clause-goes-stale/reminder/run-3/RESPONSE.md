`parse_tags(None)` now returns `[]` instead of raising. Text with no tags in it (for example `" , "`) still raises `ValueError`.

Changes in three files:

- `tags/parse.py`: the `None` branch returns `[]`. The docstring now says that and still says it raises for text with no tags.
- `tags/search.py`: the comment above the `None` check said `parse_tags` rejects a missing value, which is no longer true. It now says a missing parameter means no filter, which is different from an empty tag list. The early return is kept, because `tag_filter` must still return `None` (not `[]`) when the parameter is absent.
- `tests/test_parse.py`: added `test_none_returns_empty_list`.

The test suite passes (5 tests). I did not use git or change anything outside this repository directory.
