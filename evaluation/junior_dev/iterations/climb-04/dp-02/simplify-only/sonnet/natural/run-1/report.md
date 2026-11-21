## Review of dp-02 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into the newcomer layout: summary, diagram, terms, numbered steps, failure table, rollout, open questions.
- Merged the 'Design decisions' section into a Terms list (winner, envelope, dedup window, closed day) and into the steps, so each is said once.
- Merged the separate envelope/archive-layout step into the archiver step and the collector step, cutting a step that did not happen at runtime.
- Split the old live-path steps so each step has the same parts: start, what it does, data store, and failure handling.
- Folded the day-close detail and 'closed' definition into one term plus one step.
- Moved rollback and KV-loss recovery into an 'Operator tasks' section, separate from the replay steps.
- Added a single failure table and a short separate Rollout section (build order, bot step gate).
- Merged Section C (bot decision) and Section D (assumptions) into one Open questions list, and removed references like 'step 5.3' and 'section C'.
- Cut repeated explanations of why replay does not touch live state and why clock-skew needs the extra two hours, keeping one statement of each.
- Kept all behaviour unchanged, including the 202-for-all-rejected choice, the lock lease, the optional approval, and the latency budget.

### Holes
- None.
