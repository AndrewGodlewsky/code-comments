I changed `parse_tags` so that `None` returns an empty list instead of raising. Text that is present but holds no tags still raises `ValueError`.

Changes:
- `tags/parse.py`: `None` now returns `[]`. The docstring is updated to match the new behaviour.
- `tags/search.py`: the comment above the early return said `parse_tags` rejects a missing value, which is no longer true. It now says that an absent parameter means no filter, which is different from an empty tag list. The early return itself stays, because `tag_filter` still returns `None` for a missing parameter, and a test depends on that.
- `tests/test_parse.py`: added `test_none_returns_empty_list`. The existing blank-text test still expects a raise.

The tests pass (5 run, all OK).

You did not say why `None` should now mean "no tags" rather than an error, so the code records only the new behaviour and no reason. If there is a reason, such as a caller that passes `None` for an empty search box, please send it and I will add it beside the code.
