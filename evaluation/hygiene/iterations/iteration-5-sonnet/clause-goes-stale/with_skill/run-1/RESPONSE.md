`parse_tags(None)` now returns `[]`. Text with no tags in it, such as `" , "`, still raises `ValueError`. I added a test for the `None` case, and the tests pass.

I also fixed two comments that the change made false:
- The `parse_tags` docstring said it raises on `None`. It now says it returns an empty list for `None` and raises only when non-None text holds no tags.
- In `tag_filter` (`tags/search.py`), the comment said `parse_tags` rejects a missing value. I reworded it to say that an absent parameter means no filter (`None`), which is different from the empty list `parse_tags` returns for `None`. The early return is still needed so that absent-parameter behaviour stays the same.
