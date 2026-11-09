`parse_tags(None)` now returns `[]` instead of raising `ValueError`. Text that is a string with no tags (for example `" , "`) still raises `ValueError`.

Changes, all in the repository directory:

- `tags/parse.py`: the `None` branch returns `[]`, and the docstring describes the new behaviour.
- `tags/search.py`: the comment above the `None` check said `parse_tags` rejects a missing value, which is no longer true. It now explains that a missing parameter means no filter, which is different from an empty tag list. `tag_filter` still returns `None` when the parameter is absent, so its behaviour is unchanged.
- `tests/test_parse.py`: added `test_none_returns_empty_list`. The existing blank-text test still checks that the `ValueError` is raised.

Tests: all 5 pass (`python3 -m unittest discover -v`).

One thing to be aware of: callers that relied on `parse_tags(None)` raising will now get `[]`. I searched only the files in this repository; any code outside it was not checked.
