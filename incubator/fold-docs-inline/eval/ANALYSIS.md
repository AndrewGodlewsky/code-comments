# fold-docs-inline: eval analysis

## Iteration 1

### What was run, and what it can show

- **Scope.** The training split only: five cases, four arms. Haiku had 3 runs per cell (60 runs) and Sonnet 2 per cell (40 runs). Both iterations' `skill-snapshot/` copies of `SKILL.md` match v1 byte for byte, so every `with_skill` run read the same text.
- **Grades** are the recorded `grading.json` of each run. They include 18 rulings in 15 run folders, each in that run's `overrides.json`. All were made by an auditor agent, not a human. No grade was changed for this analysis. (Corrected after the held-out run: this line first said 15 overrides.)
- **Read order.** The audit agent ran `verify-reads` on both iterations and stored its result in each folder's `verify-reads.json`, written outside the harness: every skill-arm run (30/30 Haiku, 20/20 Sonnet) read its snapshot `SKILL.md` before its first edit. `verify-reads` counts only Edit, Write, MultiEdit and NotebookEdit calls as edits, not Bash. The auditors checked the Bash order by hand, and that check is not stored. (Corrected after the held-out run: this line first said the read order was unverified, because the audit record had not been read.)
- **Sample size.** Two or three runs per cell detect only large effects. The largest difference between `with_skill` and `reminder` on any check is 3/3 against 0/3 (Haiku, `ops-notes-in-file-sections`). A Fisher exact test on that table gives p = 0.10, two-sided, and it comes from one case. Totals summed over a model pool checks that are not independent: one decision can fail two or three checks in a run. Read the totals as descriptions, not as tests.
- **Placement** rows (`weight: 0.5`, counted in Core by the harness) passed in every run of every arm. They separate nothing and are shown apart below.
- **Held-out exposure.** While orienting I read GATE.md and CASES.md, which summarise both held-out cases. I did not open their files under `cases/`, `references/` or `hidden/`. No v2 change draws on them. Each change rests on the `with_skill` training runs quoted below.

### Headline (what the runs show)

Core excludes the placement rows. Words and list items are means over every reply in the arm. List items count lines that start with a number or a bullet.

**Haiku (15 runs per arm)**

| Arm | Mean pass rate | Checks | Core | Placement | Preservation | Restraint | Reply | Words | List items |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 97.4% | 132/135 | 32/33 | 9/9 | 36/36 | 26/27 | 29/30 | 416 | 13.0 |
| reminder | 94.8% | 128/135 | 30/33 | 9/9 | 33/36 | 26/27 | 30/30 | 264 | 6.7 |
| shipped_skill | 71.3% | 95/135 | 18/33 | 9/9 | 30/36 | 18/27 | 20/30 | 203 | 5.3 |
| without_skill | 71.4% | 96/135 | 18/33 | 9/9 | 30/36 | 18/27 | 21/30 | 197 | 4.7 |

**Sonnet (10 runs per arm)**

| Arm | Mean pass rate | Checks | Core | Placement | Preservation | Restraint | Reply | Words | List items |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| with_skill | 100.0% | 90/90 | 22/22 | 6/6 | 24/24 | 18/18 | 20/20 | 326 | 9.9 |
| reminder | 100.0% | 90/90 | 22/22 | 6/6 | 24/24 | 18/18 | 20/20 | 223 | 5.8 |
| shipped_skill | 89.1% | 79/90 | 18/22 | 6/6 | 24/24 | 13/18 | 18/20 | 165 | 3.8 |
| without_skill | 82.8% | 75/90 | 17/22 | 6/6 | 23/24 | 13/18 | 16/20 | 165 | 3.6 |

`with_skill` failed 3 checks in 25 runs, all on Haiku. They came from two runs.
- **`restatement-only-page` run 1** failed core 01 and reply 06. Both come from one decision.
- **`ops-notes-in-file-sections` run 3** failed restraint 05.

### Per case

#### `ops-notes-in-file-sections`

Checks passed per run: Haiku `with_skill` 9, 9, 8; `shipped_skill` 4, 4, 4; `reminder` 7, 7, 6; `without_skill` 5, 4, 6 (of 9). Sonnet `with_skill` 9, 9; `shipped_skill` 8, 8; `reminder` 9, 9; `without_skill` 8, 9.

Runs show:
- **with_skill, all five runs:**
  - kept the #fin-ops step, the sandbox wipe and the key rotation on the slimmed page;
  - moved the PAY-31 and idempotency reasons into comments;
  - gave every claim a fate in the reply.
- **with_skill, Haiku run 3:** the reply's fate list marks "`send_refund()` posts the refund ... and returns the provider's refund id" as Dropped. The same run then created a `send_refund` docstring whose first line is "Post the refund and return the provider's refund id.", which fails restraint 05. The run also kept the bullet "`needs_second_approver(amount)` is true for refunds of 500 EUR or more" on the page, because the code has no currency (ungraded).
- **with_skill, the EUR unit on Haiku (ungraded):** three runs, three treatments.
  - Run 1 wrote "Amounts are in EUR" into the threshold comment, which takes a value about this code from the page, and asked the user to confirm it.
  - Run 2 left the unit out and listed it as a gap.
  - Run 3 kept the whole bullet, as described above.
- **reminder, Haiku:** every run put at least one operational note into code, failing core 01 and preservation 02 in 3/3:
  - run 1 put #fin-ops at `can_send`;
  - run 2 put #fin-ops and the key rotation in code;
  - run 3 put the key rotation in code, and also restated the 500 EUR threshold (restraint 05).

  Run 2 also left a "Moved into code comments ..." note on the page (ungraded).
- **reminder, Sonnet:** both runs were clean.
- **shipped_skill, Haiku:** all three runs left the page whole. They copied both reasons and both operational notes into code, and added a docstring restating the return value. Two replies gave the return-value claim no fate, and the third fails the same check by override.
- **shipped_skill, Sonnet:** both runs were clean apart from restating docstrings (restraint 05 0/2).
- **without_skill:** every Haiku run put the operational notes into code, as both Haiku gate runs did. Sonnet was clean apart from one restating docstring.

Interpretation:
- The skill's explicit Kept list (operational steps, facts about other systems no code relies on) is the likely cause of the one large Haiku difference from the reminder.
- The reminder's "keep anything with no code to sit beside in a document" did not stop Haiku when a note names a function.
- Sonnet needs neither: every Sonnet arm kept the notes out of code.

#### `restatement-only-page`

Checks passed per run: Haiku `with_skill` 5, 7, 7; `shipped_skill` 5, 5, 7; `reminder` 7, 7, 7; `without_skill` 5, 5, 6 (of 7). Sonnet `with_skill` 7, 7; `shipped_skill` 7, 7; `reminder` 7, 7; `without_skill` 5, 5.

Runs show:
- **with_skill, Haiku run 1** added `# Standard library only: this module takes no third-party dependencies.` above the import. Its reply explains: "The page states this as a constraint on future edits, which the code does not show, so I moved it rather than dropping it." This fails core 01, and reply 06 by override.
- **with_skill, Haiku run 3** weighed the same sentence, called it "the closest call", and dropped it: "it reads as a constraint, but the import list shows it completely". Run 2 dropped it without comment.
- **with_skill, Sonnet:** both runs dropped it.
- **with_skill, overall:** no run gave `is_blank` a docstring.
- **reminder:** clean in every run (Haiku 3/3, Sonnet 2/2).
- **shipped_skill, Haiku:** run 1 added the csv note and an `is_blank` docstring, run 2 added the csv note, and run 3 was clean. Sonnet was clean.
- **without_skill:** every run on both models gave `is_blank` a docstring that restates its one-line body. Haiku run 1 also added the csv note.

Interpretation:
- The Moved fate lists "constraint", and v1 does not say whether a sentence that only describes the code may be read as one.
- Haiku run 1 filled that gap with a rule the page does not state, and widened it ("no third-party dependencies" for "only uses the standard library's `csv` module").
- The skill prevented the `is_blank` docstring that every bare run wrote, but so did the reminder.
- On this case the reminder did better by one run.

#### `slim-page-one-home`

Checks passed per run: Haiku `with_skill` 11, 11, 11; `shipped_skill` 6, 7, 6; `reminder` 11, 11, 11; `without_skill` 6, 9, 6 (of 11). Sonnet `with_skill` 11, 11; `shipped_skill` 8, 8; `reminder` 11, 11; `without_skill` 10, 8.

Runs show:
- **with_skill, all runs:**
  - slimmed the page to its title and "Who to ask";
  - moved both reasons;
  - left `AGENTS.md` untouched, and reported its FIN-88 line by file and line.
- **with_skill, Haiku runs 1 and 2** added each reason as a new paragraph inside the existing docstring. The summary lines were left word for word, which passes preservation 08.
- **with_skill, Haiku run 1's reply** lists 13 lines for a page of three paragraphs and a two-sentence section. The list includes:
  - "# Billing heading: kept";
  - "## Who to ask heading: kept";
  - "which list items by SKU: moved with claim 9";
  - "returns a `Decimal`", "rounded to the cent" and "adds up the line amounts" as three separate Dropped lines.
- **reminder:** 11/11 in every run.
  - Haiku moved "Who to ask" into an existing document and deleted the page. The graders allow this, since the note stays in exactly one document.
  - Sonnet slimmed the page.
  - Every reminder run reported the `AGENTS.md` duplicate.
- **shipped_skill:** left the page whole in every run on both models (core 01 and 02). Haiku also extended the accurate docstrings ("..., sorted by SKU"), which fails preservation 08. The `AGENTS.md` duplicate was reported in 1/3 Haiku runs and 0/2 Sonnet runs.
- **without_skill:** left the page whole in 2/3 Haiku runs and 1/2 Sonnet runs, and extended the docstring in every Haiku run. The duplicate was reported in 1/3 Haiku runs and 0/2 Sonnet runs.

Interpretation:
- The README expected the per-claim fate list and the instruction-file report to be where the skill differs from the reminder. The reminder met both duties in 5 of 5 runs, although its sentence asks for neither.
- This case shows the skill beating `shipped_skill` and `without_skill`, not the reminder.

#### `spec-claim-code-disagrees`

Checks passed per run: Haiku `with_skill` 8, 8, 8; `shipped_skill` 7, 6, 7; `reminder` 8, 8, 8; `without_skill` 6, 6, 6 (of 8). Sonnet `with_skill` 8, 8; `shipped_skill` 7, 8; `reminder` 8, 8; `without_skill` 6, 7.

Runs show:
- **with_skill, all runs:**
  - deleted the page and moved the ACC-30 reason;
  - quoted the case-insensitivity claim as not migrated, with `normalise_name`'s body as evidence, and asked which side is right;
  - wrote no ACC-12 text in code.
- **with_skill, Haiku, all three runs** created a `grant_role` docstring that opens "Set an account's role." before the ACC-30 reason. No grader anchors that line. Sonnet used a `#` comment.
- **reminder:** clean in every run, with a `#` comment at `grant_role`.
- **shipped_skill, Haiku:**
  - run 2 wrote `TODO(ACC-12)` into `normalise_name` (core 01);
  - every run added restating docstrings;
  - run 1 kept the page with an "Open conflict" note.
- **shipped_skill, Sonnet:** run 1 added restating docstrings.
- **without_skill:** every Haiku run and Sonnet run 1 wrote ACC-12 into a comment, as an unmet requirement or a to-do. Every run added restating docstrings.

Interpretation:
- The skill and the reminder both keep the disputed rule out of the code. Bare runs wrote it in 4 of 5.
- "Set an account's role." is the same behaviour as the graded failure in `ops-notes-in-file-sections` run 3: when Haiku with the skill places a moved fact at a symbol with no docstring, it creates one and opens it with a summary of what the code does.

#### `stale-number-elsewhere`

Checks passed per run: Haiku `with_skill` 10, 10, 10; `shipped_skill` 9, 9, 9; `reminder` 10, 10, 10; `without_skill` 9, 9, 8 (of 10). Sonnet `with_skill` 10, 10; `shipped_skill` 9, 9; `reminder` 10, 10; `without_skill` 8, 9.

Runs show:
- **with_skill, all runs:**
  - moved the OPS-19 reason to the retry loop and the 250 rule to `PAGE_SIZE`;
  - quoted "2 seconds apart" as not migrated, with the 2, 4, 8 and 16 second pauses;
  - added no restating comment;
  - asked which pause is right.
- **with_skill, Haiku run 1** opens the `PAGE_SIZE` comment with "Orders requested per page." (ungraded, mild).
- **reminder:** 10/10 in every run.
- **shipped_skill:** restated paging or `upsert` in every run (restraint 05).
- **without_skill:** restated in every run.
  - Haiku run 3 wrote "not a fixed 2 seconds between attempts", which fails core 01 by override.
  - Sonnet run 1 rewrote the settings comment, which fails preservation 07.

Interpretation:
- Only one run in 20 (bare Haiku, by override) wrote the stale spacing into a comment. Every reply flagged it.
- The case separates the arms on restraint, not on the stale claim.

### What the skill prevented, failed to prevent, or caused

**Prevented.** The rate is `with_skill` against the bare model; the reminder is shown for comparison.
- **Operational notes put into code (Haiku):** `with_skill` 0/3, `reminder` 3/3, `without_skill` 3/3, `shipped_skill` 3/3. This is the only check where `with_skill` beats the reminder.
- **The retired page left whole while its facts are copied into code** (`slim-page-one-home`): 0/5 against 3/5 bare. The reminder also prevented it.
- **Restating docstrings for dropped claims** (`is_blank`, paging, `upsert`, `NameTaken`, the return value): graded in 1 of 25 runs, against most bare runs. The reminder also prevented it.
- **The disputed rule written into code as a to-do:** 0/5 against 4/5 bare. The reminder also prevented it.
- **Accurate docstrings extended:** 0/5 against 3/5 bare. The reminder also prevented it.

**Failed to prevent (Haiku only).**
- **A created docstring opening with a summary of what the code does.** This happened in 4 of 15 runs, one of them graded (`ops-notes-in-file-sections` run 3) and three ungraded (`spec-claim-code-disagrees` runs 1 to 3). The reminder, which asks for "one comment", created no docstring in 25 runs. Bare Haiku created one in 12 of 15 runs.
- **A sentence that only describes the code moved as if it were a rule.** This happened in 1 of 3 runs (`restatement-only-page` run 1). A second run named it a close call.

**Caused (interpretation).**
- **Longer replies.** `with_skill` replies are the longest in every case on both models.
  - Haiku: 416 words against 264 for the reminder and about 200 for the bare and shipped arms.
  - Sonnet: 326 words against 223.
  - List items are about twice the reminder's: 13.0 against 6.7 on Haiku, 9.9 against 5.8 on Sonnet.
  - Part of the length is the deliverable: a per-claim fate list with evidence. Part is noise: headings listed as claims, and fragments of one sentence given separate lines though they share a fate (Haiku `restatement-only-page` run 2 lists 9 lines for five sentences, all Dropped).
  - v1 asks for both: step 1 splits "wherever parts could differ in truth", and the fate list has "one line per claim".
  - Sonnet split mostly where fates differed.
- **The created-docstring habit may be helped by v1's wording** ("in the file's comment style", "comments or docstrings") in files where most symbols have docstrings. This is a guess. Bare Haiku created docstrings even more often, so the skill lowered the rate rather than raising it.

**No preservation harm.** `with_skill` passed every preservation check (36/36 and 24/24): code unchanged, hidden tests passing, no file added, `AGENTS.md` byte-identical, accurate comments kept. Its one restraint failure is the created docstring above.

### Does with_skill beat the other arms?

**Haiku**
- **Against `reminder`:**
  - core 32/33 against 30/33, all checks 132/135 against 128/135, mean pass rate 97.4% against 94.8%;
  - preservation 36/36 against 33/36; restraint 26/27 each; reply 29/30 against 30/30.
  - The whole core and preservation gap is one case, `ops-notes-in-file-sections`: 3/3 against 0/3 on two checks that one decision per run fails together. The reminder did better on `restatement-only-page` by one run.
  - Interpretation: a probable advantage on one behaviour (operational notes that name code stay in a document) and a tie elsewhere. One case is not enough to call a general win.
- **Against `shipped_skill`:** core 32/33 against 18/33, mean pass rate 97.4% against 71.3%. The gap is large and spread over four of five cases. The shipped skill scored no better than the bare model (71.3% against 71.4%).
- **Against `without_skill`:** core 32/33 against 18/33, mean pass rate 97.4% against 71.4%.

**Sonnet**
- **Against `reminder`:** identical, 90/90 each. A tie on every focus.
- **Against `shipped_skill`:** core 22/22 against 18/22, mean pass rate 100% against 89.1%. The gap comes from the page left whole in `slim-page-one-home` and from restating docstrings.
- **Against `without_skill`:** core 22/22 against 17/22, mean pass rate 100% against 82.8%.

**Reply checks.** The reply checks the README expected the skill to win (the per-claim fate list and the instruction-file report) were passed by the reminder in every run on both models. On these cases the reply checks do not separate the skill from the reminder.

### Decision: one revision (v2)

v2 makes three changes. Each targets a behaviour seen in `with_skill` training runs. Each is written about the behaviour and names nothing from a case. The full wording and reasons are in [CHANGES.md](CHANGES.md).

1. **A created docstring holds only the moved fact.** The Moved fate now says to prefer a comment, or an existing docstring. A docstring the agent creates gets no opening line saying what the code does. This targets the 4 of 15 Haiku runs above.
2. **A description is not a rule.** The Dropped fate now says that a claim which only describes what the code is or does stays dropped, even if it could be read as a rule. It moves as a constraint only when the page states the rule or gives its reason. This targets `restatement-only-page` run 1, and the "closest call" run 3.
3. **One fate-list line per sentence, split only where fates differ.** Headings are not claims. This targets the reply noise above. It keeps the split for checking and for sentences whose parts have different fates.

Not revised, and why:
- **The Kept list.** It produced the only clear advantage over the reminder.
- **The unit the code does not state** (`ops-notes-in-file-sections`, three Haiku runs, three treatments). Nothing grades it, and the right fate is unclear: a gap, kept, or moved after the user confirms. It is a question for the user, not a rule to add from three runs.
- **The extended-docstring placement** (`slim-page-one-home` Haiku runs 1 and 2). It passed preservation, and v1 already allows adding beside an accurate comment.
- **Anything about the stale-claim fates.** No `with_skill` run let a stale claim through, so there is no failure to fix.

What iteration 2 should check:
- whether Haiku `with_skill` still creates docstrings with a restating first line;
- whether `restatement-only-page` holds at 3/3 on core 01;
- whether reply length and list items fall without any reply check regressing. A merged line must still name each claim.
- that the ops-notes advantage over the reminder on Haiku survives;
- the held-out split, run once at the end, as the check on overfitting.

## Iteration 2

### What was run

- **Scope.** v2, `with_skill` only, on the five training cases: Haiku 15 runs, Sonnet 10. Both snapshots are byte-identical to the current `SKILL.md`.
- **Comparisons are across runs.** The other arms were not re-run. v2 is compared with their iteration-1 runs, which did not read this skill, so the edit cannot change them; but they are separate samples.
- **Read order.** `verify-reads` found all 25 transcripts; every run read the snapshot before any edit.
- **Rulings.** One ruling, by an auditor agent.

### Result

Haiku 99.3% (134/135), Sonnet 100% (90/90).

The only failure is `ops-notes-in-file-sections` Haiku run 3, restraint 05, by ruling:
- **The comment:** "Refunds of this amount or more need a second approver. The amount is in EUR." above `SECOND_APPROVER_THRESHOLD`.
- **Why it fails:** it restates the page's threshold claim with "this amount" in place of "500 EUR". The run's own fate list marks that claim Dropped.
- **Ruled to a different standard from iteration 1.** Two iteration-1 Haiku runs wrote the same paraphrase and were not ruled on: `with_skill` run 2 and `reminder` run 2.
  - Applying the iteration-2 ruling to both would lower iteration 1 by one check in each of those arms.
  - Withdrawing it would give v2 135/135.
  - Neither changes a comparison. A human should settle which standard applies; RESULTS.md gives both sets of numbers.

The checks the iteration-1 decision asked for:

| Check | v1 (iteration 1) | v2 (iteration 2) | Read |
| --- | --- | --- | --- |
| Haiku creates a docstring that opens with a line restating the code | 4/15 runs | 0/15 | Change 1 worked on these cases. Two v2 runs created a `send_refund` docstring holding only the idempotency reason, and `grant_role` got a `#` comment in 3/3. |
| `restatement-only-page` core 01, Haiku | 2/3 | 3/3 | Change 2 worked on these cases. All three runs deleted the page and added nothing. |
| Reply length, Haiku | 416 words, 13.0 list items | 423 words, 14.7 list items and table rows | **Change 3 had no measurable effect.** Two v2 Haiku replies used a table, so items and rows are counted together. Sonnet went from 326 to 313 words and from 9.9 to 8.9 items, within run-to-run variation. |
| Reply checks still pass | 29/30 Haiku, 20/20 Sonnet | 30/30, 20/20 | No regression from merged lines. |
| Ops notes stay out of code, Haiku | 3/3 (the reminder 0/3) | 3/3 | The one Haiku advantage over the reminder held. |

**Decision: no v3.** Two of the three changes fixed their targets, and the third did no harm. The held-out pair was run next, on v2.

## Held-out cases

### What was run, and what it can show

- **Scope.** v2, all four arms, on the two held-out cases (`four-fates-page`, `stale-ordering-reason`). Haiku 3 runs per cell (24 runs), Sonnet 2 (16 runs). They ran once, after the last skill edit.
- **Exposure before the run.**
  - No skill edit drew on these cases.
  - The derivability gate did run the bare model on them before any evaluation. `stale-ordering-reason` was rebuilt from that gate run ([GATE.md](GATE.md)), so its design was shaped by bare-model behaviour.
  - The v2 writer read GATE.md and CASES.md, which summarise both cases (see Iteration 1, "Held-out exposure").
- **Rulings.** 8 rulings by auditor agents (two audits; the second kept all 8 from the first):
  - `shipped_skill`: 3 to fail and 4 to pass;
  - `without_skill`: 1 to fail;
  - none in `with_skill` or `reminder`.
- **Excluded runs.** Two Haiku runs, `reminder` run 2 and `without_skill` run 1 on `stale-ordering-reason`, were excluded and re-run.
  - The run-limits guard had blocked the heredoc writing their reply: it read `qty > 0` as a redirect.
  - The replacements are the graded runs, and the originals are in `iterations/heldout-haiku/excluded-runs/`.
- **Read order.** `verify-reads` found all 20 skill-arm transcripts. Each read the snapshot before any Bash or edit call; this was checked by hand, since the Sonnet runs edited through Bash.
- **Sample size.** 2/2 against 0/2 has a two-sided Fisher exact p of 0.33, and 0/5 against 3/5 has 0.17. Nothing here is significant on its own.

### Headline

Core excludes placement (`weight: 0.5`).

| Model | Arm | Mean pass rate | Checks | Core | Placement | Preservation | Restraint | Reply | Words |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Haiku | with_skill | 93.3% | 56/60 | 13/15 | 5/6 | 15/15 | 11/12 | 12/12 | 450 |
| | reminder | 95.5% | 57/60 | 13/15 | 6/6 | 14/15 | 12/12 | 12/12 | 265 |
| | without_skill | 82.8% | 50/60 | 15/15 | 6/6 | 12/15 | 7/12 | 10/12 | 194 |
| | shipped_skill | 79.3% | 47/60 | 9/15 | 6/6 | 13/15 | 10/12 | 9/12 | 220 |
| Sonnet | with_skill | 100.0% | 40/40 | 10/10 | 4/4 | 10/10 | 8/8 | 8/8 | 348 |
| | shipped_skill | 88.6% | 35/40 | 8/10 | 3/4 | 9/10 | 7/8 | 8/8 | 188 |
| | reminder | 81.8% | 32/40 | 6/10 | 2/4 | 8/10 | 8/8 | 8/8 | 213 |
| | without_skill | 73.5% | 29/40 | 5/10 | 4/4 | 7/10 | 5/8 | 8/8 | 199 |

### Per case

#### `four-fates-page`

Checks passed per run (of 11):
- Haiku: `with_skill` 11, 9, 11; `shipped_skill` 8, 7, 8; `reminder` 11, 11, 8; `without_skill` 10, 9, 10.
- Sonnet: `with_skill` 11, 11; `shipped_skill` 6, 11; `reminder` 7, 7; `without_skill` 7, 7.

Runs show:
- **with_skill, all five runs:**
  - slimmed `docs/digests.md` to its heading, the nightly-cleanup sentence and the #mail-ops note;
  - moved MAIL-71 to `SUBJECT_LIMIT`;
  - quoted the 24 hours as not migrated, with `MIN_HOURS_BETWEEN_DIGESTS = 6`;
  - kept the cleanup sentence as a claim about a job outside the repository, and listed it as a gap. That fate is ungraded.
- **with_skill, NOTIF-9:** four runs moved the reason to `MIN_HOURS_BETWEEN_DIGESTS` without the 24 hours. Haiku run 2 did not: "I quoted the whole sentence, including the reason ... I treated the reason as part of the contradicted value." That fails core 02 and the placement row.
- **reminder, Haiku:** runs 1 and 2 deleted the page and moved #mail-ops into `docs/oncall.md`, which the graders allow. Run 3 left the page whole and copied #mail-ops into `docs/oncall.md` as well. That fails both reason checks and "in exactly one document".
- **reminder, Sonnet:** both runs left the page whole. Run 1's reply: "docs/digests.md itself is untouched, since you're removing it". Both copied the cleanup note into README.md and #mail-ops into `docs/oncall.md`, and both left the NOTIF-9 reason out "because it explains the 24-hour figure". That is 7/11 in each run.
- **shipped_skill:**
  - Haiku left the page whole in 3/3 runs and copied every reason into code.
  - Its replies gave the grouping claim no fate in 3/3 runs, by ruling.
  - Haiku run 2 and Sonnet run 1 added "Group ... by project" at `build_digest`.
- **without_skill:**
  - Haiku deleted the page in 3/3 runs, moved NOTIF-9 into code without the 24 hours, and moved #mail-ops into `docs/oncall.md`.
  - Sonnet left the page whole in 2/2 runs, with the reasons copied into code and #mail-ops copied into `docs/oncall.md`.
  - Four of five bare runs restated the grouping at `build_digest`.

Interpretation:
- The case separates the arms on one decision, whether the page is edited at all, and the skill made that decision correctly in 5/5 runs.
- The request says the page "is going away". All nine runs that left the page whole (reminder 3, shipped 4, bare 2) said they had not deleted it, most of them leaving that to the user. The skill's Edit step ("Remove every moved, dropped and not-migrated claim from the page") makes editing the page part of the task. That is a plausible cause, not a tested one.
- The partly true claim did not separate the skill from the others. Every arm kept the 24 hours out of code in every run. Bare Haiku moved the reason in 3/3 runs; the skill did in 4/5.

#### `stale-ordering-reason`

Checks passed per run (of 9):
- Haiku: `with_skill` 7, 9, 9; `shipped_skill` 9, 7, 8; `reminder` 9, 9, 9; `without_skill` 7, 7, 7.
- Sonnet: 9, 9 in every arm except `without_skill` 9, 6.

Runs show:
- **with_skill, all runs:**
  - deleted the page;
  - moved MKT-204 to `MAX_FEED_QTY`;
  - reported the ordering claim as out of date because `write_feed` sorts its own input.
- **with_skill, Haiku run 1** split the stale claim:
  - it moved the rule part ("`stock_rows()` must return rows sorted by SKU") into the `stock_rows` docstring as "Rows must stay sorted by SKU.";
  - it reported only the reason part ("a row that arrives out of order is silently skipped") as not migrated, and told the user to remove the docstring line if the rule no longer matters.

  That fails core 01 and restraint 04.
- **reminder:** 9/9 in every run on both models.
- **without_skill, Haiku, all three runs:**
  - extended the `stock_rows` docstring with ", sorted by SKU" and the no-stock rule, which fails restraint 04;
  - rewrote the `write_feed` docstring to say both inputs are sorted there, which fails preservation 06.
- **without_skill, Sonnet run 2** added "write_feed() sorts its input itself, so callers do not depend on this ordering" at `stock_rows`. The check fails any line there that names `write_feed`, negated or not.
- **shipped_skill, Haiku:** runs 2 and 3 rewrote or extended docstrings. Run 2's comment inside `write_feed` passed core 01 under the check's exemption for true statements about `write_feed` sorting its own input.

Interpretation:
- The stale check is near ceiling: 18 of 20 runs kept the coupling out, including 4 of 5 bare runs. The rebuild after the gate did not leave much headroom.
- The skill's one failure is the split step applied to a claim whose only stated reason is stale. The page states a rule, and the v2 Dropped sentence moves a rule "only when the page itself states the rule or gives a reason for it". This page does state it, so the run moved it; nothing in v1 or v2 says what to do when the stated reason is itself contradicted. This is a hypothesis about the cause, from one run.

### Does with_skill beat the other arms on the held-out pair?

- **Against `shipped_skill`:** ahead on checks on both models (Haiku 56/60 against 47/60, with core 13/15 against 9/15; Sonnet 40/40 against 35/40), but not established at run level: full marks 8/10 against 4/10 (stratified exact p = 0.14), full core 8/10 against 6/10 (p = 0.60). Before three auditor rulings on shipped stale-ordering-reason runs (Haiku run-1, Sonnet runs 1 and 2), shipped full marks were 1/10 (p = 0.0067).
- **Against `without_skill`:** yes on the totals: Haiku 56/60 against 50/60, Sonnet 40/40 against 29/40. Full marks 8/10 against 1/10 (p = 0.0067); full core 8/10 against 7/10 (p = 1.0).
  - On Haiku the bare model did better on core (15/15 against 13/15).
  - The skill's lead there is restraint, preservation and reply: restating docstrings, rewritten docstrings and claims given no fate.
- **Against `reminder`:**
  - Haiku: a tie on core (13/15 each), with the reminder one check ahead overall (57/60 against 56/60).
  - Sonnet: 40/40 against 32/40. All eight checks come from the two reminder runs that left the `four-fates-page` page whole. Leaving the page whole fails three checks in each run on its own, as the bare Sonnet runs show. Leaving the NOTIF-9 reason out of the code adds the placement row. Core 02 fails for both reasons.
  - This is the reverse of training, where the lead was on Haiku and Sonnet tied.
  - Interpretation: on new cases, the skill's advantage over the reminder is mostly the page-handling decision, seen in one case on one model. It is not a general win.

### What the held-out pair says about generalisation

**Carried over:**
- **The page decision.** Slim when a kept note remains, delete when none does, never leave the page whole: 0 of 10 held-out runs left it whole, as in 0 of 50 training runs.
- **No preservation harm:** 25/25.
- **Restraint:** 19/20.
- **A fate for every claim:** 20/20 reply checks.

**Did not carry over:** the Haiku lead over the reminder. The training Haiku lead rested on operational notes that name a function, and neither held-out case tests that.

**Weak point:** on Haiku, the split boundary, in both directions.
- Run 2 of `four-fates-page` did not split off a true reason from a stale value.
- Run 1 of `stale-ordering-reason` split off a rule whose only reason was stale.

The README expected the split to be where the skill adds most over the reminder. On these cases it did not: the reminder made neither error on Haiku, and both Sonnet reminder errors on NOTIF-9 came with leaving the page whole.

### Decision

No edit to the skill from these results. Held-out cases are never used to decide a skill edit, and this pair is now spent: it cannot judge a later version.

If the split boundary is to be worked on:
1. Build training cases for both errors: a true reason attached to a stale value, and a rule whose only stated reason is stale.
2. Ask the user what fate each should get.
3. Build a fresh held-out pair before running a v3.
