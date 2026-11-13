# change-drift-sweep: derivability gate, 2026-11-11

The gate asks whether a case can show a gain at all. Each case ran **without any skill**:
Haiku twice (`iterations/gate-haiku/`) and Sonnet once (`iterations/gate-sonnet/`). A
case whose core checks pass in every run is at ceiling: no skill can beat a bare model
there.

Gate runs are for case selection only. No skill edit was decided from them, and SKILL.md
was not read to design the hardening below.

The held-out cases appear here only as counts. Their details, and what changed in them,
are in [HELD-OUT.md](HELD-OUT.md), which whoever edits the skill does not read.

## Results per case

Checks passed per run, as graded at the time of the gate. "Core every run" is whether
every `focus: core` check passed in all three runs.

| Case | Held out | Haiku run 1 | Haiku run 2 | Sonnet run 1 | Core every run | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `default-value-drift` | no | 6/7 | 7/7 | 6/7 | no | Headroom shown. Haiku run 1's failure was a grader bug (below); Sonnet's was real. |
| `unit-spelled-ttl` | no | 6/6 | 6/6 | 6/6 | yes | At ceiling. Hardened. |
| `derived-backoff-total` | no | 6/6 | 6/6 | 6/6 | yes | At ceiling. Hardened. |
| `flag-rename-records-stay` | no | 7/7 | 7/7 | 7/7 | yes | At ceiling. Hardened. |
| `pre-existing-drift-reported` | no | 6/6 | 6/6 | 6/6 | yes | At ceiling. Hardened. |
| `pointer-comment-needs-nothing` | yes | 6/6 | 6/6 | 6/6 | yes | Left at ceiling on purpose: a restraint control (see HELD-OUT.md). |
| `poll-interval-average-wait` | yes | 6/6 | 6/6 | 6/6 | yes | At ceiling. Hardened (see HELD-OUT.md). |

What the runs did:
- **`default-value-drift`.** Sonnet changed `PAGE_SIZE` and `docs/api.md` only. It left
  "50 rows per request" in the `exporter/client.py` docstring and "fifty at a time" in
  the `exporter/sync.py` docstring. That is the miss the case was built for. Both Haiku
  runs fixed all four statements.
- **The four training cases at ceiling.** Every run fixed every graded statement and
  kept every record and outside fact. The fixtures explain why it was easy. Each
  repository had 7 to 12 files. Every statement to fix either contained the old number
  or its word (15 and fifteen; four, 4, 7 and seven; `--since`; 100 and a hundred), or
  sat in a file that such a search already opened: the 200 POSTs in `docs/oncall.md`,
  one line below "seven seconds". The runs left only diffs and replies, not
  transcripts, so how each run searched is not known.

## Grader fix

**`default-value-drift` check 02 read the ledger's 500-row limit as a page size.** Haiku
run 1 rewrote `docs/api.md` as "The exporter asks for 200 rows per page (`PAGE_SIZE` in
`exporter/config.py`), within the ledger's 500-row limit." The sentence is true: 200 is
the new page size and 500 is the ledger team's limit, an outside fact. The new-figure
check counted every "N rows" in a changed sentence, so it read "500-row" as a page size
and failed the run.

Fix: the page-size reader in `grade.py` (`C1_SIZE`) leaves out a 500 that the words
around it mark as the limit ("500-row limit", "up to 500", "more than 500", "accepts
500"). Any other 500, such as "500 rows per page", still fails. Three variants pin it:
`good-limit-cited-beside-new-size` (the run's own wording), `good-limit-cited-as-up-to`
and `bad-page-size-set-to-the-limit`. Regraded with the fix, Haiku run 1 passes 7/7 and
Sonnet run 1 still fails check 02 on the same two docstrings.

No check was loosened to let a bad result pass. One check written during this
hardening had a bug that its variant caught before any run: `derived-backoff-total`
check 04 did not accept "tries each alert six times" as a retry count in the runbook.
It now does.

## Hardening

Each training case at ceiling gained statements that a search for the old number and
its word does not find, while keeping the request, the behaviour under test and every
existing trap. All the evidence a run needs is in the repository. The new statements
sit mostly in files that never name the changed setting, so the edit at the constant
does not lead to them.

| Case | Added living statements (a run must fix) | Added lures (a run must leave) | Why a bare model may now miss |
| --- | --- | --- | --- |
| `unit-spelled-ttl` | `auth/forms.py` docstring: a form left idle for "a quarter of an hour" cannot be saved (becomes half an hour). `docs/console.md`: the "Still there?" banner appears "after 14 minutes", the timeout less the new `IDLE_WARNING_S` (60 s), and becomes 29 minutes. | none new; the reset-link, lockout and identity-provider 15s remain | Neither statement contains 15, fifteen or 900. The banner time is an offset, and must be recomputed, not copied (30 minutes is wrong). |
| `derived-backoff-total` | `docs/runbooks/gateway-maintenance.md`: the sender "retries each alert three times" (attempts less one, becomes five). `alerts/worker.py` docstring: a backlog of 40 alerts clears "in under five minutes" in a full outage (40 times about 7 s; becomes about 21 minutes). | none new; the 7-day retention remains | Neither contains 4, four, 7 or seven. The backlog figure is derived from a derived figure, in another unit, in a caller that never names `MAX_ATTEMPTS`. |
| `flag-rename-records-stay` | `docs/cli.md`: "`--since` shares its name and meaning with the API's filter". The same page shows the orders API's filter is `since`, so after a mechanical replace the claim spells `--after` and is false. | The orders API's own `since=` query on the same page (an outside fact); `docs/incidents/2026-07-14-missed-night.md`, whose command is what was run that day (a record). | A search for `--since` finds the line, but the obvious edit (replace the flag) leaves a false claim. The records and the API query punish a replace that is too broad. |
| `pre-existing-drift-reported` | `docs/billing.md`: a burst of 1,000 notifications "costs 10 calls" (1,000 / 100; becomes 4). `notify/sender.py` docstring: at 20 calls a second one app can push "at most 2,000 notifications a second" (becomes 5,000). | The provider's 20 calls a second in the sender docstring. | Neither contains 100 or hundred; "1,000" does not match a search for 100. Both must be computed. |

The pre-existing flush mismatch, the reply check and every other trap of
`pre-existing-drift-reported` are unchanged.

Every new statement and lure is pinned by a variant in `test_grade.py` (107 variants
now, 34 of them good results worded another way). New checks or statements:
- `unit-spelled-ttl` 02 and 03 read the new forms; 03 also needs the banner time in
  `docs/console.md`. The hidden tests check the banner at 29 minutes and that
  `IDLE_WARNING_S` stays 60.
- `derived-backoff-total` 02 to 04 read the retry count and the backlog time; 04 also
  needs the runbook's retry count. The hidden tests check a full-outage drain.
- `flag-rename-records-stay` 02 fails a living sentence that still says `--after`
  shares the API filter's name (a heuristic; a sentence that says the names differ
  passes); 05 adds the incident report; 06 covers the API query.
- `pre-existing-drift-reported` 02 reads the two worked-out figures.

## What the hardening does and does not show

Replaying each gate run's exact edits on the hardened fixtures (the hunks of its
`changes.diff`, applied to the new `files/`) gives:

| Case | Haiku run 1 | Haiku run 2 | Sonnet run 1 |
| --- | --- | --- | --- |
| `unit-spelled-ttl` | fails 02, 03 | fails 02, 03 | fails 02, 03 |
| `derived-backoff-total` | fails 02, 04 | fails 02, 04 | fails 02, 04 |
| `flag-rename-records-stay` | fails 02 | fails 02 | fails 02 |
| `pre-existing-drift-reported` | fails 02 | fails 02 | fails 02 |

That shows only that the edits which passed before are no longer enough. It does not
show that a bare model will miss the new statements: a run on the new files may search
more widely or read every file. Whether each case now has headroom needs a new gate run
on the hardened cases. Until then the headroom is a hypothesis.

The gate's run records in `iterations/gate-*/` are kept as they were graded. They match
the fixtures as they were then, not the hardened ones.
