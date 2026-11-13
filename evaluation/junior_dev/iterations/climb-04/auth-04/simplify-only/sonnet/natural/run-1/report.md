## Review of auth-04 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-to-three sentence summary of the main flow at the top, before the existing-system description.
- Added a short Terms section (attempt, mode, sub, pending link), each in one line.
- Trimmed the existing-system section: removed the repeated 'no new session type' bullet, since the summary now says it.
- Merged the schema bullets about NULL password_hash and passwordless users into two shorter bullets.
- Shortened the state table: renamed the lifetime column to 'Removed by', cut repeated cookie flags and the 'latest attempt wins' / 'one callback honoured' explanations that duplicated the terms and flowchart.
- Merged the Redis-down note into a single sentence and dropped the 'eviction cannot create a link' line.
- Added two short notes after the flowchart (BACK as the shared return point, the password loop) instead of leaving the reader to infer them.
- Tightened failure-table wording and the decisions list (merged the last bullet's phrasing, removed repeated explanations).
- Added an explicit empty Open questions section at the end.
- Left the flowchart itself unchanged.

### Holes
- None.
