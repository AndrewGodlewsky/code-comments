## Review of feat-02 (rewrite-v7, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Merged the Decisions bullet list into notes placed after the diagram; each fact now appears once (the diagram keeps flow, the notes add counter, header and failure details).
- Added a two-to-three sentence summary that first states how the gateway works today, then the new flow and why Redis is shared.
- Added a Terms section: Key Service, Redis, Lua script, window, fail open.
- Added one clause saying the 120 s expiry covers the window.
- Collected failure behaviours into one table (401, 429, backend failure, Redis error or timeout, outage, plan change) instead of scattering them.
- Moved Limits and the Enterprise-unlimited-until-set rule into a separate rollout section, apart from how the system runs.
- Moved the open Enterprise limit into a closing Open questions section.
- Cut repeated statements: the 'single clock avoids skew' wording, the repeated 'no read-then-write' and 'Open items' text, and the second telling of 429 behaviour.
- Kept every stated number, header, metric name, key format, formula and the 2x boundary trade-off; no facts dropped.

### Holes
- None.
