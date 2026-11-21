## Review of ml-01 (junior, author haiku, seeded-implicit)

Rounds: 4. Ended: teachback-correct.

### What changed
- Rewrote the plan as a summary, a terms list, numbered steps and open questions, with each step naming its trigger, data, state and failure handling.
- Defined the online store, popular list, registry aliases and the 6-hour age rule, which the first version left out.
- Added the per-request feature check and the fallback triggers: read timeout, no record, stale record, missing feature, and model error or overrun.
- Added a 15-second poll and an in-memory previous version so that rollback fits the 1-minute limit.
- Made shadow work a non-blocking queue write with a separate worker, and marked a candidate with missing features as skipped.
- Defined the 10% shadow group by a fixed hash of user ID.
- Specified the prediction log and the daily comparison contents, and stated who sees the report.
- Stated the promotion gate as four required checks, and left the Product A/B step as a gap without choosing either option.
- Moved the unanswered questions into an open questions section.
- Step 3: the model deadline is now 120 ms after the request arrives, so the 30 ms fallback read still fits in the 150 ms budget. Stated that the model always gets at least 90 ms.
- Step 4: the popular-list read has its own 30 ms limit. If it also fails, the endpoint returns 503 and raises an alert. Added an open question about this case.
- Step 5: stated that fallback responses are never shadowed.
- Picking up a change: stated that instances switch on their own polls, so mixed active versions can last up to 15 seconds.
- Shadow start: shadow workers poll the shadow alias like instances do. Jobs that arrive before the candidate loads get a 'candidate not loaded' skipped row.
- Shadow worker: added a 150 ms run limit. A run past it counts as an error.
- Prediction log: removed the fallback flag, because only step 3 responses are shadowed, so it would always be false.
- Daily comparison: added the trigger (daily, after the UTC day ends), the day definition and the days-in-shadow count, the error-rate definition and denominator, and the p99 rule for timeouts.
- Promotion: the registry refuses to move active to a candidate until all four checks are recorded and pass.
- Rollback: stated that the promotion checks do not apply, because previous was already active.
- Terms: added the shadow worker.
- Step 3: added that the step records which version ran and how long the model call took, so the request path has both values.
- Step 5: the shadow job now carries the active version ID and the active model's latency from step 3, in addition to the active top 20. This answers Q19, which showed the job was missing these fields.
- Prediction log: stated that the active fields come from the job and the shadow fields come from the worker, and that the worker does not call the active model.
- Daily comparison: each daily report now also stores attempts, errors and per-bucket latency counts, so the 7-day figures can be pooled (answers Q20).
- Promotion: check 1 now says a report must exist for each of the last 7 UTC days; checks 2 and 3 are pooled over the 7-day window, with the p99 computed from pooled latency counts (answers Q20).
- Rollback Pickup: states that the 1-minute limit comes from the brief's requirement that a rollback take effect within 1 minute (answers Q21).
- Added a 'What this is' summary that first says how the system works today (a nightly precomputed table), then gives the main flow and why it is shaped that way. The two design rules are stated once here.
- Added a Terms section defining each name a newcomer would not know: online feature store, materialization job, registry, feature list, alias, feature check, popular-items list, shadow group, shadow queue, shadow worker, prediction log, daily report, and pooled latency counts. Answers Q1, Q5 and Q13 by defining these terms.
- Split the document into 'How the system runs' (request path, feature freshness, model loading, shadow, daily comparison) and 'How we roll out a model' (promotion, switch, rollback), so the runtime is kept apart from the rollout.
- Put each failure handling rule at the step it belongs to, and did not repeat them in a separate table, so each rule is stated once.
- Request steps now name the feature list the model needs, and the model's 120 ms deadline leaves 30 ms for the fallback read (Q11). Fallback to 503 stays after the popular-list read fails (Q12).
- Shadow worker now loads the candidate in the background and runs the feature check before use (Q13). Shadow start and skipped rows are stated in one place.
- Removed the fallback flag from the prediction log row, because fallback responses are never shadowed (Q15). The log has no fallback field.
- Added the reason for the 150 ms worker limit and the timeout rule in the daily comparison: timeouts count at 150 ms in the p99 (Q18). Defined the 'UTC day' and 'days in shadow' rules in one place (Q14).
- Stated that checks 2 and 3 pool all seven days, with the reason, and that each daily report keeps the counts behind the pooled p99 (Q20). Promotion now says a move of active is refused until all four checks are recorded.
- Added the source of the 1-minute rollback limit (the fixed requirement) in the rollback pickup line (Q21). Stated plainly that the 15-second poll meets it only while the registry is reachable.
- Replaced the phrase 'the brief' with plain statements of what is required, so a newcomer does not need the original request. Removed references to codes such as R3 or Q7.
- Kept every requirement from the request and the first version: endpoint and 20 IDs, 150 ms p99, 30 ms feature read, 6-hour staleness, immutable numbered versions, exactly one active version, no redeploy, rollback in 1 minute, fixed 10% shadow hash, shadow never shown or slowing the response, no model on missing features, 7 days, 0.5% error, 80 ms p99, ML lead approval, and the undecided A/B gap, which the plan leaves open.
- Open questions list now holds the six unresolved items from the answers (A/B test, candidate set, better recommendations, item features, prediction log access, the popular-list failure response). Nothing was invented to fill them.

### Holes
- Q2: How does the endpoint get 20 items from the model? Does the model score all items, or a candidate set, and where does that set come from? (author: The brief does not say whether the model scores every item or a candidate set, or where a set would come from. The plan states only that the model returns a top 20 list. This is an open question.)
