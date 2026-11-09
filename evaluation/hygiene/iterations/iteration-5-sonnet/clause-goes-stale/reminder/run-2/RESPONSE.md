`parse_tags(None)` now returns `[]` instead of raising. Text with no tags in it (for example `" , "`) still raises `ValueError`. The unit tests pass.

Comments I fixed:
- The `parse_tags` docstring said it raised for `None`. It now says `None` returns an empty list and that `ValueError` is raised only for non-`None` text with no tags.
- In `tags/search.py`, the comment "parse_tags rejects a missing value, so return early" was no longer true. I kept the early return, because `tag_filter` still has to return `None` (no filter) rather than `[]` when the parameter is absent. The comment now says that.

I added a test, `test_none_returns_empty_list`, in `tests/test_parse.py`.
