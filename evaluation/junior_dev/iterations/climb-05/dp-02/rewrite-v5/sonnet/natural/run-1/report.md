## Review of dp-02 (rewrite-v5, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into the skill layout: summary paragraph, terms, numbered steps, failure table, build order, assumptions, open questions.
- Added a Terms section defining event, received_at, duplicate, log/offset, raw archive, envelope, KV store, closed day, replay and staging.
- Added to each step what starts it, where data lives and what happens on failure.
- Merged the Design decisions list into the summary and the steps, and kept the flow diagram.
- Merged live-path steps 7 and 8 (freshness and monitoring) into one step.
- Merged replay steps 13 and 14 into a single enrich-into-staging step and merged the former steps 12 and 13 wording where they overlapped.
- Added the reason for needing raw days D-8 through D in the eligibility step.
- Added a failure table, and added the assumption that SDKs do not retry a 202 with rejections.
- Cut the repeated reasoning about 8-day TTL, per-key ordering and idempotency, and removed cross-references like step numbers where the step can stand alone.
- Renumbered replay steps 8 to 15 and moved delivery order out under the heading How to build it, separate from how the system runs.

### Holes
- None.
