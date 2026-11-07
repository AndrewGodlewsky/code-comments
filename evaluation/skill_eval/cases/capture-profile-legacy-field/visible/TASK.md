# Rename the profile name field

Implement the profile part of the v3 naming decision in
`docs/api-v3-naming.md`: profile responses should carry `display_name`
instead of `name`. While you're there, people with a blank name (missing,
empty or whitespace only) currently show up as an empty string; use their
`username` instead.

Read the whole thread before changing the response shape.
