`parse_tags(None)` now returns `[]` instead of raising. Text with no tags in it (such as `" , "`) still raises `ValueError`. The tests pass.

- `tags/parse.py`: changed the `None` branch and updated the docstring to match.
- `tests/test_parse.py`: added a test for the `None` case. The existing blank-text test still covers the raise.
- `tags/search.py`: I left the early return in `tag_filter` alone, because an absent parameter should still mean "no filter" (`None`), not an empty list. Its comment said `parse_tags` rejects a missing value, which was no longer true, so I reworded it.
