`parse_tags(None)` now returns `[]` instead of raising. Text with no tags in it (for example `" , "`) still raises `ValueError`. I ran the tests and they pass.

- `tags/parse.py`: the `None` case returns `[]`, and the docstring says so.
- `tests/test_parse.py`: added a test for `None` returning `[]`. The existing test for blank text raising is unchanged.
- `tags/search.py`: I fixed a comment that had become wrong. It said "parse_tags rejects a missing value", which is no longer true. I kept the early `return None` because a missing `tags` parameter means "no filter", which is different from an empty tag list. The comment now says that. Behaviour is unchanged.
