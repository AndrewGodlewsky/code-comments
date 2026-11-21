## Review of infra-02 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Moved the summary to the top: two or three sentences on how it works today, the main flow and why it is shaped that way.
- Added a Terms section with plain one-line definitions for SHA/tag, SSM and its two parameters, stable/canary, forward-only migration, smoke tests, lock, approval job, descendant, superseded, deployment window, Prometheus and #deploys/ANN.
- Moved the how-to-read-the-diagram bullets to just before the diagram and cut the repeated trigger/read/write explanation; kept the diagram unchanged.
- Added a Notes on the steps section after the diagram that follows run order. It merges the old canary-not-recorded, rollback-semantics, deployment-window, migration, author-check and integration-retry bullets into the step they belong to, so each fact appears once.
- Merged the repeated no-rollback-after-failed-rollout reasoning into step 3 and the gaps list, and the repeated 72 h and window explanations into steps 4 and 5.
- Shortened the multi-merge section to the three decisions and pointed back to steps 3 and 5 instead of retelling the lock reasons.
- Added the Prometheus query itself to the canary section, from environments.md, so readers do not have to look it up.
- Renamed What carried over from the existing files to Existing behaviour the pipeline relies on and kept only state, rollback, schema-after-failure and CI abilities; the rest moved into the steps.
- Added an Open questions section at the end: registry tag immutability, and whether CI can exclude the author natively.
- Checked against the first version for dropped facts: every number, limit and rule is kept, including 72 h, 5 min re-check, 15 min, 30 s, 60 s warm-up, 1%, 300s rollouts, 2 pods, 10% traffic, 3 canary-off retries, the window, the group, and the single integration retry.

### Holes
- None.
