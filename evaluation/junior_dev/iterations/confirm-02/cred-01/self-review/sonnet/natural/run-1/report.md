## Review of cred-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short opening paragraph saying what the feature is, the stack, and that session login is unchanged, so a reader new to the project has context.
- Defined 'active' and 'stale' once in a terms list before first use, instead of defining 'active' after the state table and leaving 'stale' implicit.
- Spelled out CSPRNG at first use in the token generation bullet.
- Reworded the limit/name-uniqueness bullet into a clearer sequence of steps, and labelled the limit as 10 active tokens.
- Clarified that the last-used write repeats the stale condition in its WHERE clause, which is why concurrent requests yield one write.
- Made the lost-create-response bullet start with the situation, so it reads as a cause and effect.
- Kept the diagram, failure table, and assumptions unchanged.
- Added definitions for session routes and API routes, and a plain-language gloss for CSPRNG, base62 rejection sampling and CSRF.
- Reworded the limit/name-uniqueness decision as a numbered list of transaction steps and explained why a partial unique index cannot be used.
- Clarified the uniform-401 explanation: malformed headers are rejected before any database query, and one query covers unknown, revoked and expired.
- Added a short intro to the diagram explaining the colored flows and that Flow 3 is made by the script or CI job.
- Added a Note in Flow 4 marking the post-revoke API request as a later event by a client.
- Added the missing 'Show message' step after the name-in-use 409 for consistency with the limit case.
- Split the failure table's name row into 400 (invalid) and 409 (in use), added malformed to the bad-token row and already revoked to the 404 row, to match the diagram.
- Replaced 'under 1 hour' / 'one effective write' phrasing with clearer wording, and renamed the index assumption to 'user_id' to match the column.
- Fixed 'lost response' wording from 'replay' to 'send again' to avoid jargon.
- Reordered the Terms list and added a CSPRNG definition up front, so the term is defined before its first use.
- Renamed 'Session routes' to 'Settings routes' and described both route types by path, so they match the diagram and the later text.
- Moved token format and generation to the top of the decisions list and tied it to the uniform first-use definition of CSPRNG and rejection sampling.
- Rewrote the limit and uniqueness decision to say plainly why a database constraint cannot be used, and simplified the numbered steps.
- Corrected the claim that last-used is 'less than 1 hour' out of date to 'at most about 1 hour old', which matches the stale logic.
- Reworded the lost-response explanation, the uniform 401 and the Flow 3 and Flow 4 intro lines to be shorter and more direct.
- Added a note under the failure summary that the database-error row is not drawn in the diagram.
- Changed the 'single-column unique index' assumption to 'a unique index' and made the CSRF assumption wording firmer.
- Fixed a Mermaid arrow written as 'S--xB' to 'S--xB' with the same meaning kept, and left all diagram content otherwise unchanged.

### Holes
- None.
