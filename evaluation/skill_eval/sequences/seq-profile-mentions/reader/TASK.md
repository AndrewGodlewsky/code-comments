# Serializers for @-mention autocomplete

The comment box is getting @-mention autocomplete, which needs two helpers in
`serializers.py`:

- `mention_json(user)` returns exactly `{"id": ..., "display_name": ...,
  "handle": ...}`. `display_name` must be the same value the person's profile
  response shows, and `handle` is `"@"` followed by their `username`.
- `mention_suggestions(users, prefix)` returns `mention_json` entries, in input
  order, for the people whose `username` or display name starts with `prefix`
  (ignoring case). Only suggest people the member directory would list.

This is a new endpoint for the new comment box, so no existing client reads it.
Leave the profile and directory responses as they are.
