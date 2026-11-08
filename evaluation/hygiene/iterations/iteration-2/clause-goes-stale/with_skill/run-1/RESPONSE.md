`parse_tags(None)` now returns `[]` instead of raising. Text with no tags (e.g. `" , "`) still raises `ValueError`.

Changes, all in the outputs repository:
- `tags/parse.py`: the `None` branch returns `[]`. The docstring now says so, and still says that no-tag text raises.
- `tags/search.py`: the comment above the early return said `parse_tags` rejects a missing value. That is no longer true, so I rewrote it. The early return stays, because `tag_filter` must still return `None` (no filter) for an absent parameter, which is distinct from an empty list.
- `tests/test_parse.py`: added `test_none_returns_empty_list`. All 5 tests pass.

Two things to check:
- I did not find a reason for the `None` -> `[]` behaviour in the request, tests or code, so the code and docstring record only the new behaviour. Could you tell me why `None` should be treated as an empty list? If there is a reason, it belongs beside the branch in `parse.py`.
- `tag_filter` still treats a missing parameter as "no filter" and returns `None`, not `[]`. If you wanted missing input to be `[]` everywhere, that is a separate change to `search.py` and its test.
