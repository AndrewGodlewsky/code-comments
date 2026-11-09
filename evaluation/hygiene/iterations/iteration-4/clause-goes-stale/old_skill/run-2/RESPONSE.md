`parse_tags` now returns an empty list when `text` is `None`. It still raises `ValueError` for text with no tags in it, such as `" , "`.

Changes:
- `tags/parse.py`: the `None` branch returns `[]` instead of raising. The docstring now says "Returns [] if text is None. Raises ValueError if text holds no tags."
- `tags/search.py`: the comment in `tag_filter` said `parse_tags` rejects a missing value, which is no longer true. It now says `parse_tags` returns `[]` for a missing value and that the early `None` return keeps an absent parameter as "no filter". The early return stays, because `tag_filter({})` must still return `None` (the existing test checks this), not `[]`.
- `tests/test_parse.py`: added `test_none_gives_empty_list`.

Tests: `python -m unittest tests.test_parse` runs 5 tests, all passing.

Open question: you did not say why `None` should now give an empty list, so I recorded no rationale beyond the docstring. If there is a reason (for example, that absent search parameters should behave like an empty filter), tell me and I will add it beside the code.
