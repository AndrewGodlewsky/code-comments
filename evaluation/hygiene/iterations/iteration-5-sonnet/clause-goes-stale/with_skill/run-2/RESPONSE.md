`parse_tags(None)` now returns `[]`. Text with no tags in it, such as `" , "` or `""`, still raises `ValueError`.

- `tags/parse.py`: changed the None branch and updated the docstring, which said it raised for None.
- `tags/search.py`: the comment in `tag_filter` said "parse_tags rejects a missing value", which is no longer true. I reworded it to say an absent parameter means no filter (`None`), where `parse_tags` would give `[]`. The early return stays so that behaviour is unchanged.
- `tests/test_parse.py`: added a test for the None case.

I ran `python -m unittest` below.
