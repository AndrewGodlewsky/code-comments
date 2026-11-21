## Review of dp-01 (junior-v4, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a Window section: the window is set once per run_date and stored in the run log, retries and reruns reuse it, and rows after the cutoff are excluded (Q1).
- Defined run_date as the UTC date of the 02:00 trigger in Terms (Q2).
- Added a 'When a night fails for good' section stating that nothing reruns automatically and that the next night's window covers the missed night (Q3).
- Made the recovery note an explicit step (step 6) and a diagram node, posted by the committing attempt when the commit is after 06:00 UTC (Q4).
- Split failure paths in the diagram: failures before the transaction go straight to FAILED and drop staging; failures inside it roll back first (Q5).
- Defined one run-log row per attempt, written STARTED by the scheduler, with crash handling and a SUCCEEDED check before each retry (Q6).
- Stated that dashboards show a late commit at their next 06:00 refresh and added this as an open question (Q7).
- Added a Why nothing is lost section with the window arithmetic, and an open question on the 30-day reconciliation limit (Q8).
- Merged the 'What starts each step' and 'Where state lives' tables into Terms and the numbered steps, and consolidated failure rules into one table. Removed the duplicated retry rules.
- Removed a stray character at the start of the file.
- Added an Attempt process term and said which process runs steps 2 to 5 and which writes FAILED (Q9).
- Window is now stored on every attempt's run-log row. Attempt 1 sets it and later attempts copy it, replacing the wrong claim that one row holds it (Q11).
- Step 1 now checks for SUCCEEDED and STARTED rows before any start, including a manual rerun, and says a manual rerun takes the next attempt number outside the three scheduled attempts (Q12).
- The scheduler drops a dead attempt's staging table when it marks that attempt FAILED (Q10).
- The notes say the scheduler starts a retry only after the previous process exits (Q13). The scheduler-restart gap was added to open questions.
- Defined visible as committed and replicated. The 90-minute bound now covers commit delay only, not replica lag (Q14).
- Added to the failure section that the HWM stays behind during a failed night and moves only on a later commit (Q15).
- Stated that reconciliation has no time limit and may overlap with the Monday load, and added that to open questions (Q16).
- Rewrote steps so each has the same four parts: starts when, does, keeps its data, if it goes wrong. Failure handling is one table. Steps 1 to 5 replace the old steps 1 to 7, and the Failure step moved into the table.
- Cut duplicated wording in the window, reconciliation and visibility sections, and shortened the assumptions. The merge rule, window bounds, three attempts, 06:00 check and Sunday reconciliation design are unchanged.
- Cut the 'Why nothing is lost' section. Kept the two facts a reader needs: the 90-minute bulk-import delay as the reason for the 2-hour lookback (in Window), and the one-night-late visibility point (in Staleness check and dashboards).
- Replaced the long Mermaid diagram with a shorter one. Removed the state nodes, the dotted read and write edges, and the staleness and reconciliation branches. Where the state lives is now a table under the diagram. Staleness and reconciliation are described in their own sections.
- Merged the separate failure notes, the failure-table rows and the repeated dead-process explanation into one failure table. The dead-process rule now appears once in the notes and once in the table.
- Removed repeated wording: 'steps 2 to 5 run inside the attempt process' now appears once, and the staging-drop rule appears once under step 5 and once in the Staging term. The manual-rerun start check now lives only in 'When a night fails for good', and step 1 points there.
- Added a Status term (STARTED, SUCCEEDED, FAILED) so the step text is plain. Added 'if it goes wrong' lines to the steps that were missing them, and gave each step the same four parts.
- Moved the staleness check and the Sunday reconciliation into their own sections after the failure table, so the steps read as one flow. Kept the MERGE SQL, the checksum rule, the window and rerun rules, the assumptions and the open questions as they were.
- Added one open question about tied `updated_at` values for the same order. The dedupe step and the MERGE guard do not decide the tie. This is a gap found during simplification. It does not change what the plan does.

### Holes
- Q16: If the Sunday night job is still retrying at 06:00 or later, how long does reconciliation wait? Can it run at the same time as the Monday 02:00 load? (author: The reconciliation waits for the Sunday night job to reach a terminal state, with no time limit, because the brief sets none and I did not add one. Attempts are at most three, 15 minutes apart, so it usually starts well before Monday 02:00. The brief does not bound extract or reconciliation time, though, so the two can overlap if the reconciliation is slow. Data stays correct because both write through the same guarded merge. Whether the warehouse allows two MERGEs into dw.orders at once is unknown, and it is an open question in the file.)
