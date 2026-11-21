## Review of mr-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short glossary (RPO, RTO, WAL, replay lag, epoch) so a reader new to the stack can follow.
- Defined fencing in plain words at the start of section 2 and stated that the command sets active=B when moving to FENCING.
- Replaced the confusing preflight decision node in the flowchart with a clean branch on the record's state (A_ACTIVE, FENCING, B_PROMOTED, B_ACTIVE), with resume edges into the right step.
- Pointed the 'command dies' edge back to the command so it matches 'rerun the same command'.
- Added a how-to-read paragraph before the flowchart.
- Fixed a resume hazard: rerunning at B_PROMOTED would have requeued jobs that B's workers were actually running. Added requeued/workers_started progress flags to the record and the rule that reruns skip the requeue.
- Clarified that the lag check runs only on a fresh run, not on a resume.
- Restructured the time budget so parallel job steps are shown as parallel and do not appear to add to the total.
- Clarified the lease TTL sentence and that A's old database is never reused as primary.
- Moved the definitions of fencing, compare-and-set and lease into the opening glossary, so later sections can use them without explanation.
- Defined replay lag in terms of when WAL is received, matching the brief, and dropped the separate 'what fencing means' sentence from section 2.
- Shortened the opening, the flowchart reading note and a few table cells.
- Fence-wait resume row now says a rerun waits the full fence period again, which matches the flowchart. It previously said 'wait out the remainder'.
- Merged the 'no region is writable' sentences in the promote-failure row.
- Reworded the jobs flag sentence to say 'either flag'.
- Renamed 'Triggers by step' to 'What triggers each step' and 'Reading it' to 'How to read it'.
- Added a short plain-language summary paragraph at the top giving the whole sequence before the details.
- Explained 'warm standby' inline for readers new to the setup.
- Made requeue skip condition consistent: flowchart now says skipped if requeued or workers_started, matching section 4.
- Specified when each progress flag is written (requeued after the transaction commits, workers_started just before workers start) and why a crash between the transaction and the flag is harmless.

### Holes
- None.
