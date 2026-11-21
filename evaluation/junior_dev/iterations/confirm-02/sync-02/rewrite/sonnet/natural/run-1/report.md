## Review of sync-02 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into: summary (with how the system works today), terms, shared rules, server API, local state, runtime steps, failure table, assumptions, build/rollout, open question.
- Merged the old step 3 (shared request rule) with the Wi-Fi gate, 15-minute limit and 4xx handling into one 'Rules that apply everywhere' section instead of repeating them per step.
- Folded the old step 7 (edits during download, not a runtime step) into step 4 as one explanatory paragraph.
- Moved server build (old step 1), local migration (old step 2) and tests (old step 13) into a separate 'Build and rollout' section, apart from how the system runs.
- Renumbered runtime steps 1-8 in the order they happen; removed the duplicate Design in brief bullets and the old routing detail repeated in steps 4 and 11.
- Added a Terms section (change_seq, watermark, keyset pagination, tombstone, generation, single-flight lock) and a one-table failure summary.
- Made step 1 routing handle catching_up and downloading explicitly, and step 4 entry cover resume from step 1.
- Cut the Design-in-brief restatements of watermark and generation logic and the duplicated sync_state/endpoint prose; kept every number, limit, field and rule.
- Added assumption 5 (6-day staging limit) as a listed assumption since it was only conditional prose before.
- Open question is retained unchanged in meaning, with step references updated.

### Holes
- None.
