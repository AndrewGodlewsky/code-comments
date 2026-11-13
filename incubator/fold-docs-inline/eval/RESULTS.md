# fold-docs-inline: results

**The skill beat the shipped `code-comments` skill and the bare model in training, on both
models. On the held-out pair it led both on checks. At run level only its full-marks lead
over the bare model held (8/10 against 1/10, stratified exact p = 0.007). Its lead over the
shipped skill is not established (8/10 against 4/10, p = 0.14; 1/10 for the shipped skill
before three auditor rulings). It did not reliably beat the one-line reminder.**

Against the reminder, by model and split:
- **Sonnet training:** a tie.
- **Haiku held-out:** the reminder was one check ahead.
- **Haiku training (+4 checks) and Sonnet held-out (+8 checks):** the skill was ahead.
  Each lead comes from a single case, and rests on 2 or 3 runs per cell.

Page handling held in every skill run. With the skill, the page was slimmed when a note
with no code home remained and deleted when none did. It was never left whole: 0 of 60
runs. The reminder left it whole in 3 of 35 runs, all on held-out `four-fates-page`. The
shipped skill did so in 12 of 35 and the bare model in 6 of 35.

These are small samples: 2 or 3 runs per cell, seven small Python cases built by agents,
one model family. The reasoning behind the numbers is in [ANALYSIS.md](ANALYSIS.md), the
skill edits are in [CHANGES.md](CHANGES.md), and case selection is in [GATE.md](GATE.md).

## What ran

Four arms, as the [incubator README](../../README.md) defines them:
- `with_skill` reads this skill's `SKILL.md` snapshot first.
- `shipped_skill` reads a snapshot of the shipped `code-comments` skill first.
- `reminder` gets the sentence in [arms.json](arms.json) added to the request. It names
  every fate: "Before moving anything off that page, check each claim against the code:
  leave out what the code already shows, don't carry over anything the code contradicts
  (tell me about it instead), put each remaining code-specific fact in one comment beside
  the code it governs and take it off the page, keep anything with no code to sit beside
  in a document, and don't change any code or create new files."
- `without_skill` gets the request alone.

Two models, Claude Haiku and Claude Sonnet. The iteration folders do not record the exact
model versions. Haiku ran 3 runs per case per arm, Sonnet 2.

| Iteration | Skill | Cases | Arms | Runs |
| --- | --- | --- | --- | --- |
| `gate-haiku`, `gate-sonnet` | none | all 7, before two were rebuilt | `without_skill` | 21, for case selection only, not counted ([GATE.md](GATE.md)) |
| `iteration-1-haiku` | v1 | 5 training | all 4 | 60 |
| `iteration-1-sonnet` | v1 | 5 training | all 4 | 40 |
| `iteration-2-haiku` | v2 | 5 training | `with_skill` only | 15 |
| `iteration-2-sonnet` | v2 | 5 training | `with_skill` only | 10 |
| `heldout-haiku` | v2 | 2 held out | all 4 | 24 |
| `heldout-sonnet` | v2 | 2 held out | all 4 | 16 |

This file counts 165 graded runs.

**Skill versions.** Each iteration keeps the `SKILL.md` its runs read in
`skill-snapshot/`:
- The iteration-1 snapshot is v1 (88 lines).
- The iteration-2 and held-out snapshots are byte-identical to the current v2 (97 lines).
- The shipped-skill snapshot is byte-identical, in every iteration that ran that arm, to
  `plugins/code-comments/skills/code-comments/SKILL.md`.

v2 made three changes ([CHANGES.md](CHANGES.md)):
1. A docstring the agent creates holds only the moved fact.
2. A claim that only describes the code stays dropped.
3. The fate list has one line per sentence, split only where fates differ.

**Iteration 2 is compared across runs.** It re-ran only `with_skill`, so v2 is compared
with the other arms' iteration-1 runs. Those arms do not read this skill, so the edit
cannot change what they do. But they are separate samples from a separate run.

**How each run started.** Each agent read its task from `prompt.txt` as its first tool
call. A real request arrives as a user's message instead. The skill arms were told to
read the skill first.

**Skill reads.** Audit agents ran `verify-reads` on every iteration:
- Every skill-arm run read its snapshot `SKILL.md` before its first edit: iteration 1
  50/50, iteration 2 25/25, held-out 20/20.
- Sonnet runs often edited through Bash, which `verify-reads` does not count as an edit.
  So the auditors also checked the tool order by hand: the skill read came before any
  Bash or edit call.
- Each iteration folder stores the result in `verify-reads.json`. An out-of-repository
  wrapper wrote these files (see [incubator/README.md](../../README.md));
  `harness.py verify-reads` only prints its result. The hand check of Bash
  order is not stored.

## Headline

From `python incubator/harness.py summary fold-docs-inline iteration-1-haiku
iteration-1-sonnet iteration-2-haiku iteration-2-sonnet heldout-haiku heldout-sonnet`.
Each cell is the mean pass rate, then checks passed.

| Iteration | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` (v1) | 97.4%, 132/135 | 71.3%, 95/135 | 94.8%, 128/135 | 71.4%, 96/135 |
| `iteration-1-sonnet` (v1) | 100.0%, 90/90 | 89.1%, 79/90 | 100.0%, 90/90 | 82.8%, 75/90 |
| `iteration-2-haiku` (v2) | 99.3%, 134/135 | not run | not run | not run |
| `iteration-2-sonnet` (v2) | 100.0%, 90/90 | not run | not run | not run |
| `heldout-haiku` (v2) | 93.3%, 56/60 | 79.3%, 47/60 | **95.5%, 57/60** | 82.8%, 50/60 |
| `heldout-sonnet` (v2) | **100.0%, 40/40** | 88.6%, 35/40 | 81.8%, 32/40 | 73.5%, 29/40 |

Pass rate is the mean of each run's share of checks passed. Every run in every arm wrote a
reply: the benchmark's "No reply" column is 0 throughout. The numbers include 27 rulings
by auditor agents (see "Rulings").

Pooled over both models, checks passed:

| Split | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| Training, iteration 1 (v1) | 222/225 | 174/225 | 218/225 | 171/225 |
| Training, iteration 2 (v2) | 224/225 | not run | not run | not run |
| Held out (v2) | 96/100 | 82/100 | 89/100 | 79/100 |

## By focus

The harness counts the placement checks (`weight: 0.5`, a secondary heuristic) inside
Core. They are split out here, so "Core" means the target behaviour without placement.
The harness's Core is the sum of the two columns. "Words" is the mean length of the
reply.

| Iteration | Arm | Core | Placement | Preservation | Restraint | Reply | Words |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `iteration-1-haiku` | with_skill | 32/33 | 9/9 | 36/36 | 26/27 | 29/30 | 416 |
| | shipped_skill | 18/33 | 9/9 | 30/36 | 18/27 | 20/30 | 203 |
| | reminder | 30/33 | 9/9 | 33/36 | 26/27 | 30/30 | 264 |
| | without_skill | 18/33 | 9/9 | 30/36 | 18/27 | 21/30 | 197 |
| `iteration-1-sonnet` | with_skill | 22/22 | 6/6 | 24/24 | 18/18 | 20/20 | 326 |
| | shipped_skill | 18/22 | 6/6 | 24/24 | 13/18 | 18/20 | 165 |
| | reminder | 22/22 | 6/6 | 24/24 | 18/18 | 20/20 | 223 |
| | without_skill | 17/22 | 6/6 | 23/24 | 13/18 | 16/20 | 165 |
| `iteration-2-haiku` | with_skill | 33/33 | 9/9 | 36/36 | 26/27 | 30/30 | 423 |
| `iteration-2-sonnet` | with_skill | 22/22 | 6/6 | 24/24 | 18/18 | 20/20 | 313 |
| `heldout-haiku` | with_skill | 13/15 | 5/6 | 15/15 | 11/12 | 12/12 | 450 |
| | shipped_skill | 9/15 | 6/6 | 13/15 | 10/12 | 9/12 | 220 |
| | reminder | 13/15 | 6/6 | 14/15 | 12/12 | 12/12 | 265 |
| | without_skill | **15/15** | 6/6 | 12/15 | 7/12 | 10/12 | 194 |
| `heldout-sonnet` | with_skill | 10/10 | 4/4 | 10/10 | 8/8 | 8/8 | 348 |
| | shipped_skill | 8/10 | 3/4 | 9/10 | 7/8 | 8/8 | 188 |
| | reminder | 6/10 | 2/4 | 8/10 | 8/8 | 8/8 | 213 |
| | without_skill | 5/10 | 4/4 | 7/10 | 5/8 | 8/8 | 199 |

Read the rows with care:
- One decision can fail two or three checks in a run. Leaving the page whole, for
  example, fails "one home" for each moved reason and "in exactly one document" for a
  kept note.
- So totals pool checks that are not independent. They describe the runs; they are not
  tests.

## Per case

Checks passed per run.

### Training, iteration 1 (v1) and iteration 2 (v2)

| Case | Model | with_skill v1 | with_skill v2 | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- | --- |
| `ops-notes-in-file-sections` (of 9) | Haiku | 9, 9, 8 | 9, 9, 8 | 4, 4, 4 | 7, 7, 6 | 5, 4, 6 |
| | Sonnet | 9, 9 | 9, 9 | 8, 8 | 9, 9 | 8, 9 |
| `restatement-only-page` (of 7) | Haiku | 5, 7, 7 | 7, 7, 7 | 5, 5, 7 | 7, 7, 7 | 5, 5, 6 |
| | Sonnet | 7, 7 | 7, 7 | 7, 7 | 7, 7 | 5, 5 |
| `slim-page-one-home` (of 11) | Haiku | 11, 11, 11 | 11, 11, 11 | 6, 7, 6 | 11, 11, 11 | 6, 9, 6 |
| | Sonnet | 11, 11 | 11, 11 | 8, 8 | 11, 11 | 10, 8 |
| `spec-claim-code-disagrees` (of 8) | Haiku | 8, 8, 8 | 8, 8, 8 | 7, 6, 7 | 8, 8, 8 | 6, 6, 6 |
| | Sonnet | 8, 8 | 8, 8 | 7, 8 | 8, 8 | 6, 7 |
| `stale-number-elsewhere` (of 10) | Haiku | 10, 10, 10 | 10, 10, 10 | 9, 9, 9 | 10, 10, 10 | 9, 9, 8 |
| | Sonnet | 10, 10 | 10, 10 | 9, 9 | 10, 10 | 8, 9 |

What separated the arms in training:
- **`ops-notes-in-file-sections`, Haiku.**
  - The operational notes (#fin-ops, the key rotation) stayed out of code in 6/6
    `with_skill` runs over v1 and v2.
  - Every other arm put them into code in 3/3 runs, which also fails "in exactly one
    document".
  - Sonnet kept them out in every arm.
- **`slim-page-one-home`.** The shipped skill left the page whole in 5/5 runs and the
  bare model in 3/5, with the moved reasons copied into code. Both also missed the
  `AGENTS.md` duplicate in most runs. The skill and the reminder were clean.
- **`spec-claim-code-disagrees`.** The bare model wrote the disputed ACC-12 rule into a
  comment as a to-do in 4/5 runs, and the shipped skill in 1/5. The skill and the
  reminder never did.
- **Restatement restraint.** In every case the shipped skill and the bare model copied
  the page's restatements into docstrings far more often than the skill or the reminder.
- **`stale-number-elsewhere` sat near ceiling on its stale check.** 19 of 20 iteration-1
  runs kept "2 seconds apart" out of the code. The only failure was bare Haiku run 3, by
  ruling. CASES.md said to report this rather than harden the case again.

### Held out (v2)

| Case | Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| `four-fates-page` (of 11) | Haiku | 11, 9, 11 | 8, 7, 8 | 11, 11, 8 | 10, 9, 10 |
| | Sonnet | 11, 11 | 6, 11 | 7, 7 | 7, 7 |
| `stale-ordering-reason` (of 9) | Haiku | 7, 9, 9 | 9, 7, 8 | 9, 9, 9 | 7, 7, 7 |
| | Sonnet | 9, 9 | 9, 9 | 9, 9 | 9, 6 |

By focus within each held-out case:
- Columns: Core without placement / Placement / Preservation / Restraint / Reply.
- Cells are summed over the runs in the cell.

| Case | Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| `four-fates-page` | Haiku | 8/9, 2/3, 9/9, 6/6, 6/6 | 3/9, 3/3, 9/9, 5/6, 3/6 | 7/9, 3/3, 8/9, 6/6, 6/6 | 9/9, 3/3, 9/9, 4/6, 4/6 |
| | Sonnet | 6/6, 2/2, 6/6, 4/4, 4/4 | 4/6, 1/2, 5/6, 3/4, 4/4 | 2/6, 0/2, 4/6, 4/4, 4/4 | 2/6, 2/2, 4/6, 2/4, 4/4 |
| `stale-ordering-reason` | Haiku | 5/6, 3/3, 6/6, 5/6, 6/6 | 6/6, 3/3, 4/6, 5/6, 6/6 | 6/6, 3/3, 6/6, 6/6, 6/6 | 6/6, 3/3, 3/6, 3/6, 6/6 |
| | Sonnet | 4/4, 2/2, 4/4, 4/4, 4/4 | all full | all full | 3/4, 2/2, 3/4, 3/4, 4/4 |

## Held-out cases: does the skill generalise?

The held-out pair is the main test of whether the skill works beyond the cases it was
revised on. No v2 edit drew on these cases. They ran once, on v2, after the last edit.
But v1 was not written blind to them. The v1 writer read CASES.md, which then described
both. The build fixer read and edited their files and, in the same session, made 6 edits
to SKILL.md ([README](../README.md) Limits). So the pair guards the v2 revision against
overfitting; it is not a blind test of v1's rules.

| Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| Haiku (6 runs per arm) | 93.3%, 56/60, core 13/15 | 79.3%, 47/60, core 9/15 | 95.5%, 57/60, core 13/15 | 82.8%, 50/60, core 15/15 |
| Sonnet (4 runs per arm) | 100.0%, 40/40, core 10/10 | 88.6%, 35/40, core 8/10 | 81.8%, 32/40, core 6/10 | 73.5%, 29/40, core 5/10 |

Core here excludes placement.

What the held-out runs show:
- **Over the bare model, the result carries over, on cases the skill's authors had seen
  (see above). Over the shipped skill, it leads on checks only.** With the skill:
  - Haiku: 56/60, against 47/60 for the shipped skill and 50/60 for the bare model.
  - Sonnet: 40/40, against 35/40 for the shipped skill and 29/40 for the bare model.
  - At run level, full marks are 8/10 against 1/10 for the bare model (stratified exact
    p = 0.007; full core 8/10 against 7/10), and 8/10 against 4/10 for the shipped skill
    (p = 0.14; 1/10 before three auditor rulings), so the lead over the shipped skill is
    not established.
  - On Haiku the skill led the shipped skill on core, preservation, restraint and reply.
    It led the bare model on preservation, restraint and reply, but trailed it on core
    (13/15 against 15/15).
  - On Sonnet it led both on core, preservation and restraint. Reply tied at 8/8.
- **Against the reminder, it does not carry over consistently.**
  - Haiku: the reminder passed 57/60 and the skill 56/60. Core tied at 13/15.
  - Sonnet: the skill passed 40/40 and the reminder 32/40.
  - The Sonnet gap is one case and two decisions. Both reminder runs on `four-fates-page`
    left the page whole for the user to delete ("docs/digests.md itself is untouched,
    since you're removing it"). They copied the kept notes into README.md and
    docs/oncall.md, and left out the NOTIF-9 reason. Leaving the page whole fails three
    checks in each run on its own, as the bare Sonnet runs show. Leaving out the reason
    adds the placement row. Core 02 fails for both reasons. With 2 runs per arm, 2/2
    against 0/2 has a two-sided Fisher exact p of 0.33.
  - So the training pattern did not repeat. In training the skill's lead over the
    reminder was on Haiku and Sonnet tied; held out, the lead is on Sonnet and Haiku is
    a tie or slightly behind.
- **Bare Haiku did best on held-out core** (15/15). It trailed the skill and the
  reminder on restraint (7/12), preservation (12/15) and reply (10/12):
  - restating docstrings;
  - the `write_feed` docstring rewritten;
  - claims given no fate in the reply.
- **The skill's two held-out failures are both Haiku, and both are about splitting a
  sentence whose parts differ in truth.** That is the behaviour the README expected the
  skill to add.
  - **`four-fates-page` run 2 did not split.** It treated the NOTIF-9 reason as part of
    the contradicted 24 hours, and left it out of the code. The reply says so: "I
    treated the reason as part of the contradicted value."
    - That fails core 02, and the placement row.
    - Both Sonnet reminder runs made the same call.
    - Every bare run (5/5) put the reason into the code without the 24 hours. The two
      bare Sonnet runs also left it on the page.
  - **`stale-ordering-reason` run 1 split too far.** The page's rule ("must return rows
    sorted by SKU") rests only on the stale reason. The run moved the rule part into
    the `stock_rows` docstring as "Rows must stay sorted by SKU.", and reported the
    reason part as not migrated.
    - That fails core 01 and restraint 04.
    - No reminder run did this.
- **The stale claims themselves were near ceiling for every arm.**
  - No run in any arm wrote the 24 hours into code (20/20).
  - 18 of 20 runs kept the stale ordering coupling out: all but the skill's Haiku run 1
    and bare Sonnet run 2.
  - Every reply in every arm flagged both stale claims (reply 10 and reply 08: 20/20
    each).
  - `stale-ordering-reason` was rebuilt after the gate to leave headroom, and the bare
    model still passed its stale check in 4 of 5 runs.

**Interpretation.** On new material the skill kept a run-level full-marks lead over the
bare model and a check-level lead over the shipped skill that is not established at run
level (8/10 against 4/10, p = 0.14), and did no preservation harm (25/25). Its edge over
the reminder is not established in either direction:
- the lead on Sonnet comes from one case where the reminder left the page whole;
- Haiku is a one-check difference the other way.

The skill's own weak point on Haiku is the split boundary, under-splitting in one run and
over-splitting in another.

## Iteration 2: did the v2 changes work?

Each v2 change is checked against its target. These are Haiku `with_skill` runs, v1 then
v2, 15 runs each.

| v2 change | Target in iteration 1 | v1 | v2 | Read |
| --- | --- | --- | --- | --- |
| 1. A created docstring holds only the moved fact | New docstrings that open with a line restating the code | 4/15 runs (1 graded) | 0/15 | Fixed on these cases. The two v2 runs that created a `send_refund` docstring wrote only the idempotency reason. `grant_role` got a `#` comment in 3/3. |
| 2. A description stays dropped | `restatement-only-page` core 01 | 2/3 | 3/3 | Fixed on these cases. All three v2 runs deleted the page and added nothing. |
| 3. One fate-list line per sentence | Reply length | 416 words; 13.0 list items | 423 words; 14.7 list items and table rows | **No effect.** Haiku replies did not get shorter. Sonnet moved from 326 to 313 words and from 9.9 to 8.9 items, within run-to-run variation. Held-out replies were longer still (450 and 348 words). |

A new single failure appeared in v2:
- **The run:** `ops-notes-in-file-sections` Haiku run 3 failed restraint 05, by ruling.
- **What it wrote:** "Refunds of this amount or more need a second approver. The amount
  is in EUR." above `SECOND_APPROVER_THRESHOLD`. Its own fate list marks that claim
  Dropped.
- **A ruling not applied evenly.** Two iteration-1 runs wrote the same paraphrase, and no
  ruling was made on them:
  - `with_skill` run 2: "refunds at or above this amount need a second approver";
  - `reminder` run 2: "Refunds of this amount in EUR or more need a second approver".

  So the two iterations were not ruled to one standard.
  - Applying the iteration-2 standard to iteration 1 would give Haiku `with_skill` v1 a
    mean pass rate of 96.6% (131/135 checks) and the reminder 94.1% (127/135).
  - Withdrawing it would give v2 135/135.
  - Either way, no comparison changes direction.

## Rulings (overrides) by arm

Every ruling was made by an auditor agent, not a human. Each sits in that run's
`overrides.json`, and the check's own result stays in the evidence. In the table, "to
fail" means the check passed and the ruling failed it; "to pass" means the reverse.

| Iteration | with_skill | shipped_skill | reminder | without_skill | Total |
| --- | --- | --- | --- | --- | --- |
| `iteration-1-haiku` | 1 to fail | 2 to fail, 1 to pass | 1 to pass | 5 to fail | 10 |
| `iteration-1-sonnet` | 0 | 0 | 4 to pass | 1 to fail, 3 to pass | 8 |
| `iteration-2-haiku` | 1 to fail | not run | not run | not run | 1 |
| `iteration-2-sonnet` | 0 | not run | not run | not run | 0 |
| `heldout-haiku` | 0 | 3 to fail, 2 to pass | 0 | 1 to fail | 6 |
| `heldout-sonnet` | 0 | 2 to pass | 0 | 0 | 2 |
| **Net checks** | **-2** | **0** | **+5** | **-4** | 27 |

**The rulings did not flatter the skill.** On the checks' own results, before any
ruling:

| Iteration | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` | 98.3% | 72.2% | 94.1% | 75.1% |
| `iteration-1-sonnet` | 100.0% | 89.1% | 95.6% | 81.1% |
| `iteration-2-haiku` | 100.0% | not run | not run | not run |
| `iteration-2-sonnet` | 100.0% | not run | not run | not run |
| `heldout-haiku` | 93.3% | 80.5% | 95.5% | 84.3% |
| `heldout-sonnet` | 100.0% | 83.1% | 81.8% | 73.5% |

What the rulings were:
- **The skill's two rulings** both failed a pass: a reply that said it moved a fact
  (iteration 1), and the threshold paraphrase above (iteration 2).
- **The reminder's five rulings** all passed a fail. Four were on two Sonnet `ops-notes`
  runs, where the anchor `idempoten` missed "refuses a second refund with the same key".
- **No ruling is a grader bug.** No check was wrong for every run.

Recurring anchor gaps, each worth fixing in `grade.py`:
- `ops-notes-in-file-sections` 03 and 04: `idempoten` misses "the same key".
- `ops-notes-in-file-sections` 09: `refund id` also matches the idempotency sentence.
- `restatement-only-page` 06: the keywords pass replies that say they moved a fact.
- `slim-page-one-home` 11: `\badds?\b` matched an unrelated "add".
- `stale-number-elsewhere` 01: the exemption for growing pauses let "not a fixed 2
  seconds between attempts" through.
- `stale-number-elsewhere` 10: the paging anchor missed "reads pages until one comes back
  empty".
- `four-fates-page` 11: the grouping anchor `build_digest` also matches where the cleanup
  note went.
- `four-fates-page` 06: the per-line allow pattern rejects the wrapped second line of the
  cleanup note.
- `stale-ordering-reason` 09: the no-stock anchors miss "empty stock", "empty-stock" and
  "zero-stock".

Close calls left as graded, not ruled:
- **`spec-claim-code-disagrees` 01:** "Case is preserved" and "matching is
  case-sensitive" pass.
- **`stale-number-elsewhere` 05:** "each request gets up to ATTEMPTS tries" passes.
- **`stale-ordering-reason` 01:** three shipped-skill comments inside `write_feed` pass.
  Each says the merge needs sorted input and that both inputs are sorted "here". The
  check exempts these on purpose, as true of the code.

## Excluded runs

Two held-out Haiku runs were excluded and re-run:
- `stale-ordering-reason` `reminder` run 2;
- `stale-ordering-reason` `without_skill` run 1.

Why:
- Each run made its edits. Then the run-limits guard blocked the Bash heredoc that writes
  RESPONSE.md: it read `qty > 0` in the reply text as a redirect to a file named `0`.
- Each agent stopped, as the guard told it to, so the run had changes but no reply.
- The cause was the environment, not the arm.

The originals are kept as evidence in `iterations/heldout-haiku/excluded-runs/`, each with
an `EXCLUDED.txt`:
- Without a reply, they graded 7/9 (reminder) and 4/9 (bare).
- The replacement runs graded 9/9 and 7/9.
- The reminder original failed only its two reply checks. The reminder's one-check lead
  on held-out Haiku rests on its replacement: with the original, the reminder would pass
  55/60, one check behind the skill.
- The bare original also failed core check 1, which its replacement passed. Of that
  replacement's 3-check gain, 2 checks come from the reply and 1 does not.

No skill-arm run was excluded, and no other run was re-run.

## What with_skill did that the others did not

- **It never left the page whole: 0 of 60 runs over v1, v2 and the held-out pair.**
  - It slimmed the page in all 25 runs whose page held a note with no code home
    (`ops-notes-in-file-sections`, `slim-page-one-home`, `four-fates-page`), and
    deleted it in all 35 runs whose page held none.
  - The reminder left the page whole in 3 of 35 runs, all on held-out `four-fates-page`.
    The shipped skill did so in 12 of 35 and the bare model in 6 of 35.
  - The checks grade this through "one home" and "in exactly one document".
  - Of the eight checks in the skill's held-out Sonnet lead over the reminder, leaving
    the page whole would fail six on its own. The other two are the placement row: the
    reminder runs left the NOTIF-9 reason out of the code.
- **On Haiku, it kept operational notes that name a function out of the code.**
  `ops-notes-in-file-sections`: 6/6 runs over v1 and v2, against 0/3 for each other arm.
  This is the source of its training Haiku lead over the reminder. Fisher p = 0.10 for
  3/3 against 0/3.
- **A kept note stayed in exactly one document** on `four-fates-page` in 5/5 runs.
  The shipped skill managed 4/5, the bare model 3/5 and the reminder 2/5.
- **It kept the big-picture note (ungraded) on the page** in 5/5 `four-fates-page` runs.
  Every reply gave the same reason: no code in the repository runs the cleanup or the
  schedule, so the claim cannot be checked here, and it was listed as a gap.
  - The shipped skill and the bare model put it in the `build_digest` docstring.
  - The reminder put it in README.md.
  - The graders accept all of these homes.
- **Its replies give every claim evidence: a file, a symbol and a value.** They are also
  the longest, 1.5 to 1.7 times the reminder's length, and v2 did not shorten them.

## What the others did that with_skill did not

- **The reminder matched it on almost everything else**, with replies about two thirds
  as long:
  - Restraint: 64/65 against the skill's 63/65, over iteration 1 and held-out.
  - Reply checks: 70/70 against 69/70.
  - The per-claim fate list and the `AGENTS.md` duplicate report: the reminder did both
    in every run, though its sentence asks for neither. The README expected the skill to
    win these.
- **The reminder created no new docstring in 35 runs.** v1 of the skill created ones that
  opened with a restating line in 4 of 15 Haiku runs. v2 fixed this on the training
  cases.
- **The reminder was cleaner where v1 failed.**
  - `restatement-only-page`: 3/3 against v1's 2/3.
  - Held-out `stale-ordering-reason` on Haiku: 3/3 against the skill's 2/3.
- **Bare Haiku moved a reason out of a partly true claim** on held-out `four-fates-page`
  in 3/3 runs, against the skill's 2/3. On these cases the skill showed no advantage at
  splitting a sentence whose parts differ in truth:
  - Every arm kept the stale value out in nearly every run.
  - The skill's held-out failures were splitting errors.
- **The shipped skill and the bare model never beat the skill on preservation, restraint
  or reply**, and trailed it on at least one of those in every iteration. On core they
  trailed it everywhere except held-out Haiku, where the bare model passed 15/15 against
  the skill's 13/15. Apart from that and shorter replies, they did nothing the skill
  lacked.

## Where the numbers come from

- Pass rates, checks and focus counts come from each iteration's `benchmark.json`, which
  `harness.py grade` writes. All 165 runs were re-graded in memory for this file, and every
  result matched its stored `grading.json`.
- Placement was split out by the grader's `weight: 0.5` frontmatter.
- Raw results come from the "check said" part of each override's evidence.
- Word counts are whitespace-separated tokens in each run's `RESPONSE.md`. List items are
  lines that start with a number or a bullet; v2 also counts table rows.
- Page states compare each run's page file with the case's original:
  - absent means deleted;
  - unchanged means left whole;
  - anything else means slimmed.
- Fisher exact p-values are two-sided. They are for comparisons chosen after reading the
  runs.
