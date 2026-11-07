# Case-insensitive account lookup at sign-in

The sign-in handler looks accounts up with `users.get(typed_name)`, an exact
match, so someone who registered as `alice` but types `Alice` is told the
account doesn't exist. `users` maps each stored username (the form sign-up
stores) to its account record.

Add `find_account(users, typed)` to `usernames.py`. It returns the matching
account record, or `None` when there is no match. It must never raise: staff
accounts such as `admin` and `support` were created directly and sign in
through the same form, and a name that would fail sign-up validation simply
has no account, so return `None` for it.

Sign-up behaviour stays as it is.
