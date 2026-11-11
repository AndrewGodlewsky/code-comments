I retired docs/accounts.md and moved its content into the code.

- accounts/names.py: the normalise_name docstring records that only surrounding whitespace is stripped.
- accounts/users.py: a comment on DEFAULT_ROLE records that new accounts are members and that only admins can grant editor (ACC-30). The register docstring covers NameTaken, and the grant_role docstring covers the admin-only rule.

docs/accounts.md is deleted. Nothing on it needs a standalone document now that these comments carry it. docs/support.md is unchanged; it is about password resets and does not describe this code.

One thing does not match. The old page said usernames are case-insensitive (ACC-12), so find_user("Ann") and find_user("ann") return the same account. The code only strips whitespace, so those names are different keys and register() accepts both. I did not write that rule into a comment as if it were true. The normalise_name docstring says the comparison is case-sensitive as implemented and that ACC-12 asks for case-insensitivity, which is not done yet. Someone needs to decide whether the intent (ACC-12) or the code is right, then fix the code or the comment.

Tests: all 3 tests in tests/test_users.py pass. I did not change any behaviour or tests.
