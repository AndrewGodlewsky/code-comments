# Invalid pilot runs: author answers dropped

These are the pilot's Junior arm runs and every judgment that involved them. They are kept
as evidence and must not be scored. The tournament harness dropped every author answer:
authors labelled ids "Q1" while `templates/tournament.js` matched "1", so 0 answers were
recorded across 8 runs. Each round the junior therefore saw "(no answer)" for every
question, kept asking, and the author kept adding text to the plan. The bug was fixed and
covered by `test_author_answers_are_recorded`, and the Junior arm was rerun into
`iterations/pilot/`.

The plugin itself was not affected: `junior.py` accepts the "Q" prefix. The headless run
`live-results/p11a-t-refunds-haiku-hooks` recorded its answers normally.

Before the fix, Junior lost every blind clarity judgment against NoReview and SelfReview
(16 of 16 pairs, both orders agreeing), with documents about 2.5 to 3 times longer. Read
that as the cost of a loop that never hears its answers, not as a measure of the skill.
