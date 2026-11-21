## Review of feat-02 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-paragraph summary at the top explaining how the gateway works today and the main flow, before the decisions.
- Added a short Terms section (customer ID, plan, window, fail open).
- Dropped the separate Redis primary/replica detail from Store; it was not needed to follow the flow.
- Removed the Time source decision, which said the gateway sends its clock yet Redis TIME is used (confusing and contradictory). Merged it into the Counter key bullet: window number comes from Redis TIME.
- Merged the Fail-open decision bullet, the Key Service note and the backend-failure rule into one failure table in Notes.
- Removed the Customer ID decision bullet; now covered by the Terms definition.
- Merged the two Known limits mentions (2x burst in Decisions and Notes) into one cost note in Decisions plus a single line in Notes.
- Moved the Enterprise Open item to a dedicated Open questions section at the end and removed the duplicate sentence in Decisions.
- Shortened the Atomicity and Retry-After wording into plainer sentences and removed requirement numbers (req. 4, 5, 7, 8) so each point stands alone.
- Left the Mermaid diagram unchanged.

### Holes
- None.
