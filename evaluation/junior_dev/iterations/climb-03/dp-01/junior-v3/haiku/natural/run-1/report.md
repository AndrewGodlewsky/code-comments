## Review of dp-01 (junior-v3, author haiku, natural)

Rounds: 4. Ended: teachback-correct.

### What changed
- Changed: Added a Terms section defining run_date, window_hi, window_lo, hwm_ts, attempt, staging and commit, so the steps can be read without the brief.
- Changed: Preflight now inserts a running row holding window_lo and window_hi when attempt 1 starts, and retries read the window and attempt count from pipeline_runs. The earlier draft stored the window only at commit.
- Changed: Preflight marks leftover running rows as timed out, so a crashed process still counts as an attempt and the retry decision stays correct.
- Changed: Extract runs inside one REPEATABLE READ replica transaction, with keyset chunks inside it. This gives one snapshot, stops a row updated mid-extract from being staged twice and failing the duplicate check, and makes extract_count meaningful.
- Changed: Added the first-run seed of ctl.pipeline_state, so the first night has a window_lo.
- Changed: Corrected the dashboard behavior. Dashboards see a night at their next refresh, not at commit.
- Changed: Reconciliation ignores order_ids changed after window_hi on both sides, to prevent false mismatches from rows that changed after the window while an older version was already loaded.
- Changed: Stated explicitly that a failed Sunday night skips that week's reconciliation, and that reconciliation failures do not affect the night's commit.
- Changed: Merged the separate Atomicity, Merge logic and High-water mark sections into Steps 5 and State, and removed the SQL. The exact statements are an implementation detail that a newcomer does not need to follow the flow.
- Changed: Replaced the node name stg.orders_<run_id> with stg.orders_run, because angle brackets in Mermaid labels are fragile.
- Changed: Replaced the scattered failure notes with one failure table that covers crashes, skipped nights, late commits, manual reruns and the 06:00 alert.
- Changed: Consolidated the assumptions and the unresolved points into one Open questions section at the end of the file.
- Terms: window_lo now explains the up-to-90-minute visibility delay that the 2-hour lookback covers (Q10).
- Terms: added trigger (scheduled or manual) and noted that manual attempts count as attempts (Q11).
- Start step: the scheduler retries only after a non-zero exit or its own 45-minute kill, and never reads ctl (Q12).
- Preflight rewritten as five ordered checks: committed row exits; live manual attempt exits; otherwise leftover running rows are marked timed out; three non-committed attempts page and exit; drop and recreate staging (Q11, Q12, Q13).
- Commit step: added the rollback rule for failures before COMMIT and the rule for an unknown COMMIT outcome (Q14).
- Failure table: split kill and crash (no row written, retry marks timed out) from caught errors; attempt 3 paths for caught errors and for kill or crash; manual start while a running row is live; timing sentence now covers the crash page path (Q11, Q12, Q16).
- Reconciliation: the reload merges only, with no hwm_ts change and no pipeline_runs row, and the Sunday process shares the 45-minute kill (Q15). The old wording 'using the nightly rules' was removed because it would have moved hwm_ts.
- Diagram: preflight, failure, reload and page nodes updated to match. Added dotted edges from extract and commit to the scheduler retry for kill or crash (Q11, Q12, Q15, Q16).
- State: pipeline_runs gains trigger and started_at; staging is dropped by the next preflight if an attempt died (Q13).
- Open questions: added the 45-minute limit as this design's choice, the same-instant start race, and rollback on session end under the warehouse transaction question (Q11, Q16).
- Preflight step 3 now applies only to scheduled starts, and it counts attempts for run_date. A manual start after a skipped night runs one attempt, which fixes the contradiction with the on-call row (Q17).
- Diagram: preflight step 3 label now says scheduled start. The P1 edge to PAGE is labelled scheduled, and the edge to E1 says including manual start.
- Diagram: the failure handler now splits three ways. Scheduled attempt 3 pages and exits 0, scheduled attempts 1 and 2 exit non-zero for the scheduler retry, and manual attempts go to a new node that says nothing retries them.
- Diagram: added a 45-minute kill edge from reconciliation to Done, so a killed Sunday run is shown.
- Start step: the scheduler retry applies only to scheduled attempts. A manual attempt is started by on-call and nothing retries it.
- Failure table: the on-call row now says a manual attempt skips the three-attempt rule. Added a row for a manual attempt that fails. Added a row for a kill during Sunday reconciliation (Q17, Q18).
- Timing paragraph: now says manual attempts fall outside the worst-case timing (Q17).
- Reconciliation: the 45-minute kill covers the whole job process, so reconciliation gets only the time the load left. Added the 40-minute load example, the stop rule and that a killed run is not resumed that week (Q18).
- Open questions: added whether Sunday reconciliation needs its own time limit (Q18).
- Step 2.3: the page count now means non-committed rows, including timed out and manual rows, and the sentence about an attempt 3 killed before writing its row was replaced by the row-based rule (Q20).
- Step 2.4: every attempt inserts its own running row with attempt number and trigger, and later attempts copy the stored window. This replaces the text that said only attempt 1 writes a row (Q19).
- Terms: attempt now says each attempt writes one row at preflight step 4 and that its attempt number is one more than the existing rows (Q19).
- Terms: window_hi now says rows updated after it wait for a later night (Q21).
- Step 3: extract_count is stored on this attempt's row, and the sentence explaining that rows after window_hi are read by the next night was added (Q21).
- Step 5: the unknown-COMMIT rule now says what the next attempt does with a missing committed row, the stored window and the leftover running row (Q22).
- Failure table: the kill or crash row now refers to the running row written at step 4, and the failure handler marks this attempt's row (Q19, Q22).
- Failure table: the attempt 3 kill or crash row now describes the retry's preflight marking the row timed out before counting (Q20).
- Failure table: the 06:00 row now says exactly what the check queries, that it runs on Sundays, and that reconciliation does not affect it (Q23).
- Diagram: P1 label, the CLOCK label, the row-writing edges and the kill or crash labels were updated to match the per-attempt row and the 06:00 check (Q19, Q22, Q23).
- Summary cut to the main flow only. The window details it repeated now live in Terms.
- Terms cut to one line each. Removed the pointer to a preflight step number and the phrase about the attempt number, which now stand on their own.
- Diagram: kept every node and edge of the original. Shortened the long node and edge labels, and moved the detailed preflight and commit rules into the Steps section.
- Steps: merged the retry description into Start. Merged the commit-failure explanation into one paragraph. Moved the deleted-order and re-run note under the steps and shortened it.
- Failure table: merged the two scheduled-attempt rows (attempts 1 and 2 fail, and attempt 3 fails with a caught error) into a pair of rows with the same rule. Kept every other failure row. Shortened the timing note to one paragraph.
- Reconciliation: removed the duplicated 45-minute-kill recovery paragraph, since the failure table already covers it. Moved the 40-minute-load remark into the 45-minute open question.
- Reload rule now says in plain words which nightly steps it reuses, instead of a step-number range.
- State: shortened each line. The pipeline_runs line keeps its reason for existing (a scheduler restart cannot reset the attempt count or window).
- Open questions: merged the two questions about the 45-minute limit (the design choice and reconciliation's share of it) into one. All other open questions are kept as written.
- No mechanism, rule or threshold was added or removed. The 45-minute limit, 15-minute gap, three-attempt rule, window, commit and checksum logic are unchanged.

### Holes
- None.
