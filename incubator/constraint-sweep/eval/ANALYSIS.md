# constraint-sweep: eval analysis

## Iteration 1

### What ran

- **Haiku** (`iteration-1-haiku`): the five training cases, four arms, three runs each, 60 runs in all.
- **Sonnet** (`iteration-1-sonnet`): the same cases and arms, two runs each, 40 runs in all.
- Both iterations read a `skill-snapshot/constraint-sweep/SKILL.md` that is byte-identical to the skill before v2 (called v1 below).
- Every run wrote a `RESPONSE.md`. No run has an `overrides.json`, so every grade below is the check's own result.
- The held-out cases were not run and were not opened for this analysis.
- The iteration folders hold no `verify-reads` or `discovery.py` output. So this analysis cannot say whether each skill-arm run read its skill before its first edit, or when each run found the evidence. The replies cite the evidence files, so finding is inferred from replies, not transcripts.

Sources: each run's `changes.diff`, `RESPONSE.md` and `grading.json`, and the two `benchmark.md` files. Word counts and diff sizes come from a throwaway script over those files.

### Headline numbers (what the runs show)

| Model | Arm | Core | Preservation | Restraint | Reply | All checks |
| --- | --- | --- | --- | --- | --- | --- |
| Haiku | with_skill | 15/15 | 27/30 | 33/36 | 15/15 | 90/96 |
| Haiku | shipped_skill | 10/15 | 27/30 | 34/36 | 10/15 | 81/96 |
| Haiku | reminder | 15/15 | 27/30 | 31/36 | 15/15 | 88/96 |
| Haiku | without_skill | 15/15 | 28/30 | 30/36 | 15/15 | 88/96 |
| Sonnet | with_skill | 10/10 | 20/20 | 23/24 | 10/10 | 63/64 |
| Sonnet | shipped_skill | 9/10 | 19/20 | 23/24 | 9/10 | 60/64 |
| Sonnet | reminder | 10/10 | 19/20 | 23/24 | 10/10 | 62/64 |
| Sonnet | without_skill | 10/10 | 19/20 | 22/24 | 10/10 | 61/64 |

- **Haiku with_skill failed six checks.** All six are in `sort-relied-on-elsewhere`: checks 04 and 07 in each of its three runs.
- **Sonnet with_skill failed one check:** check 07 of `positional-columns-in-sql`, in run 2.

### Per case and arm (what the runs show)

#### `dispatched-by-name`

- **Every run of every arm passed all six checks**: 12 on Haiku, 8 on Sonnet.
- Every run removed the same two dead functions and kept the handler that the dispatcher reaches by a name it builds at run time. The diffs are identical (9 changed lines each).
- The case sits at ceiling for every arm, so it cannot separate them.
- One Sonnet with_skill reply says the tests were not run.

#### `positional-columns-in-sql` and its pointer twin

Where each run put the new column, over both cases (Haiku six runs per arm, Sonnet four):

| Arm | Named place, load updated in step | Named place, load not updated (core fails) | Appended at end |
| --- | --- | --- | --- |
| with_skill | Haiku 6/6, Sonnet 4/4 | 0 | 0 |
| shipped_skill | Haiku 2/6, Sonnet 0/4 | Haiku 3/6 | Haiku 1/6, Sonnet 4/4 |
| reminder | Haiku 3/6, Sonnet 0/4 | 0 | Haiku 3/6, Sonnet 4/4 |
| without_skill | Haiku 0/6, Sonnet 0/4 | 0 | Haiku 6/6, Sonnet 4/4 |

- **Both outcomes are accepted.** The graders accept the preferred result (the column where the user asked, with the positional load changed in step) and the alternative (the column at the end, with the reply saying why). So the split above does not show in pass rates.
- **The only core failures** are the three Haiku shipped_skill runs that put the column where the user asked and left the load alone.
- **Unrequested edits to the finance doc** describing the new column fail check 07:
  - with_skill: 1/10 (Sonnet base run 2);
  - shipped_skill: 1/10;
  - reminder: 2/10;
  - without_skill: 4/10.
- **One with_skill run widened the scope** (Sonnet pointer run 2). It also added a currency column to the warehouse table definition and loaded the new field into it. Its own reply says an existing warehouse needs a manual `ALTER TABLE` first, 'Otherwise the 01:30 load will fail.'
  - It passed every check, because the hidden load builds the table from the edited schema and `deploy/warehouse/` is an allowed folder.
  - No other run in any arm did this.

#### `sort-relied-on-elsewhere`

What each run did with the order the upload script needs:

| Model | Arm | Database returns id order (preferred) | Python sort moved into the export path | Sort removed, order lost (core fails) | Nothing changed |
| --- | --- | --- | --- | --- | --- |
| Haiku | with_skill | 0/3 | 3/3 | 0 | 0 |
| Haiku | shipped_skill | 0/3 | 1/3 | 2/3 | 0 |
| Haiku | reminder | 0/3 | 3/3 | 0 | 0 |
| Haiku | without_skill | 0/3 | 2/3 | 0 | 1/3 |
| Sonnet | with_skill | 2/2 | 0 | 0 | 0 |
| Sonnet | shipped_skill | 1/2 | 0 | 1/2 | 0 |
| Sonnet | reminder | 1/2 | 1/2 | 0 | 0 |
| Sonnet | without_skill | 1/2 | 1/2 (an `ordered=True` flag passed from the export) | 0 | 0 |

- **Moving the sort fails two checks.** Every run that moved the ordering into the export path edited the export module, which fails check 07. It also rewrote the upload script's comment to name the new sort, which fails check 04. That rewrite follows from the move: once the sort moves, the comment's claim about the producer is false. With_skill's six Haiku failures are exactly these two checks in three runs.
- **The Haiku with_skill replies knew the alternative.** Run 1 says 'the next option is an `ORDER BY id` in SQL, which I have not tried'. Runs 2 and 3 justify the move by calling the export 'the only place that builds the bank file' and 'the only place that needs the order'.
- **The Sonnet with_skill runs kept the property where it is produced**, at the database. They touched only the producer and its docstring, with the smallest diffs of any arm (5 and 11 changed lines).
- **The shipped skill's arm broke the upload in three runs** (Haiku 2, Sonnet 1). It found the constraint each time and rewrote the script's comment to say the upload could be rejected. Each reply cites the request (Haiku run 1: 'you asked only to drop it').
- **The bare Haiku run that changed nothing** declined to act and asked the user to choose. It failed check 02 (the Python sort is still there).

#### `stale-constraint-elsewhere`

- **Every run of every arm passed all five checks.**
- **The diffs differ in one way the checks do not score.**
  - **Every with_skill run left the stale comment in place** (Haiku 3/3, Sonnet 2/2) and only reported it. Each reply calls the comment wrong now: 'now false', 'now inaccurate', 'now wrong', 'no longer true'. Three give the reason they did not fix it: the wording 'belongs to the code-comments skill'. They hand the fix to the user as a follow-up.
  - **Every run of the other three arms corrected the comment in place** (15/15), and kept the accurate comments, which check 04 confirms.
- Check 05 passes either way, because it accepts a reply that calls the comment stale.

### Failures the skill caused, failed to prevent, or prevented

- **Caused: a comment the change makes false is left in place** (`stale-constraint-elsewhere`, with_skill 5/5 against 0/15 in the other arms).
  - **What the runs show:** the with_skill replies say the comment is now false. They leave it, and cite the `code-comments` skill as the owner of the fix.
  - **Interpretation:** this follows the v1 wording closely. The intro says 'This skill asks for no comments'. The stale rule says 'report the stale text ... Any fix to that wording follows `code-comments`'. The with_skill arm does not load `code-comments`, so the deferral turns into no fix at all. That suppresses what the bare model does unprompted, and what the shipped skill requires ('fix or delete every comment your change made false ... callers' comments'). No check scores it.
- **Failed to prevent: moving the property into a consumer instead of keeping it where it is produced** (`sort-relied-on-elsewhere`, Haiku with_skill 3/3).
  - **What the runs show:** reminder (3/3) and bare (2/3) Haiku runs did the same, so the skill did not cause it. On Sonnet only the skill arm kept the producer-side fix in every run (2/2 against 1/2 for each other arm). Two runs per cell cannot separate those rates.
  - **Interpretation:** v1's option 1 ('Keep the property where it is produced, by a means that still does what was asked') is there. But Haiku read moving the work into the one consumer that needs it as a way of keeping the constraint. Nothing in v1 says relocation is not option 1, or that moving a cost to another path does not meet a request about cost.
- **Prevented, or at least not seen with the skill:**
  - **A broken constraint after the sweep found it.** The shipped-skill arm did this in 3 Haiku positional runs and 3 sort runs (Haiku 2, Sonnet 1). With_skill did it in 0 runs.
  - **Dropping the form the user named.** On the positional pair, with_skill kept the named place and updated the dependent in 10/10 runs. The other arms did so in 5/30 runs, and 3 of those 30 broke the load.
  - **Unrequested doc edits.** with_skill 1/10, the bare arm 4/10. The counts are too small to call this an effect.

### Does with_skill beat the other arms?

- **Core checks.** with_skill ties reminder and without_skill on both models: Haiku 15/15 each, Sonnet 10/10 each. It beats shipped_skill (Haiku 15/15 against 10/15, Sonnet 10/10 against 9/10). The gap over shipped_skill comes from that arm's knowing breaks. That is a harm of the shipped skill on these cases, not a gain unique to this skill.
- **All checks.**
  - Haiku: with_skill 90/96, reminder and without_skill 88/96, shipped_skill 81/96.
  - Sonnet: with_skill 63/64, reminder 62/64, without_skill 61/64, shipped_skill 60/64.
  - The leads over reminder and the bare arm are one or two checks. With two or three runs per cell, that is well inside run-to-run variation.
- **What the pass rates cannot show.** The clearest differences between arms are not scored:
  - with_skill kept the named form 10/10 on the positional pair, against 0/10 bare.
  - with_skill left a now-false comment 5/5, against 0/15 for the other arms.
- **The headroom gate.** Bare models found the cross-file evidence in every core case, and no bare run failed a core check. So iteration 1 cannot show a core gain for any arm over the bare model on these fixtures.

### Harm

- **Preservation.**
  - with_skill failed none on Sonnet.
  - On Haiku it failed three (check 04 of the sort case), the same as reminder. The bare arm failed two.
  - The ungraded stale-comment behaviour leaves false text in the repository. It harms what the next reader trusts, not the behaviour of the code.
- **Restraint.**
  - with_skill failed three restraint checks on Haiku (all check 07 of the sort case) and one on Sonnet. That is no worse than any other arm.
  - The one scope widening (an extra column and a required migration) is a with_skill run, but it is one run in ten.
- **Noise.** No with_skill diff added defensive code, and no with_skill reply asked a question.
  - Mean changed lines per run were lower with the skill: Haiku 12.1 (bare 12.7, reminder 15.8), Sonnet 9.3 (bare 14.4, reminder 14.0).
  - Part of that gap is the stale-comment fix the skill suppressed.
- **Longer replies.** Mean reply length was a little higher with the skill than bare:
  - Haiku: 215 words, against 192 bare and 269 reminder.
  - Sonnet: 196 words, against 177 bare and 204 reminder.
  - That is about 10% over bare, and less than or about equal to the reminder arm.

### Limits of this evidence

- **Two or three runs per cell detect only large effects.** A 3/3 against 0/3 split (or 5/5 against 0/15 pooled across models) is the size this design can show. One- or two-check differences in the totals are not.
- **The checks miss two of the clearest behaviours.** These are the named-form split and the stale-comment split. Both come from reading diffs and replies, not from a check.
- **The sort result on Haiku rests on one case** and three runs per arm.
- **No transcripts were read.**

### Decision for v2

One revision, two rule changes, each written about the behaviour, not a fixture. Details are in [CHANGES.md](CHANGES.md).

1. **Repair the rule that caused harm.**
   - Text a change makes false must be corrected in the same change, in any file, with `code-comments` governing only the wording.
   - A stale constraint the change does not make false is still only reported.
2. **Close the gap that let the work move into a consumer.**
   - Moving the work that provides a property out of the changed symbol and into a dependent is not 'keeping it where it is produced'.
   - Look first for another, cheaper way for the symbol itself to provide the property. Move the work only when there is none, and say why.

**What would count against v2:**
- edits to comments that state nothing, or to stale text the change did not make false (the held-out restraint case checks this);
- keeping a cost the user asked to remove;
- refusing or asking instead of acting.

The two changes touch different cases, so their effects can be read apart.

## Iteration 2

### What ran, and a correction to iteration 1

- **The runs.** `iteration-2-haiku` (15 runs) and `iteration-2-sonnet` (10 runs) ran v2 on
  the five training cases, `with_skill` only. Their snapshot is byte-identical to the
  current `SKILL.md`. The other arms were not re-run: they do not read this skill, so
  they are compared through their iteration-1 runs.
- **A correction to iteration 1.** Iteration 1's "What ran" said that skill reads were
  unverified. That is now out of date. After that section was written, the auditors ran
  `verify-reads` on all three run sets:
  - iteration 1: 50 of 50 skill-arm runs;
  - iteration 2: 25 of 25;
  - held out: 20 of 20.

  Every run read its snapshot before its first edit, and none was excluded.
  `discovery.py` was still not run on any iteration.
- **No rulings and no reruns.** No `overrides.json` was written in any iteration.

### Against what CHANGES.md expected

- **"Corrects a comment its change made false": seen.**
  - In `stale-constraint-elsewhere` all 5 v2 runs corrected or deleted the `rollup.py`
    comment. v1 corrected it in 0/5 (p = 0.008, two-sided Fisher exact).
  - No v2 reply hands the fix to `code-comments`. In v1, three replies did.
- **"Still only reports stale text it did not make false": not tested.** No training or
  held-out case has stale text that the change leaves true.
- **"Keeps the property inside the changed symbol more often" on Haiku: seen in direction
  only.**
  - Haiku `ORDER BY id` in `fetch_rows`: 2/3 runs, against 0/3 in v1 (p = 0.40). Sonnet
    stayed at 2/2.
  - The Haiku run that still moved the sort into `ledger/nightly.py` (run-1) failed
    checks 04 and 07, as in v1.
  - Its reply names `ORDER BY id` as the cheaper option and says it did not use it
    "because you asked for the sort to be dropped". So v2's new sentence was read and
    not followed in that run.
- **"No graded check is worse": held.**
  - Haiku 94/96 against v1's 90/96; Sonnet 64/64 against 63/64.
  - No check passed in fewer runs than in v1.
- **The positional rule held.** The named form was kept with the load renumbered in 10/10
  runs, again.
  - No run edited `docs/finance.md`.
  - No run repeated v1's scope widening into the warehouse table.
- **Nothing counted against v2 in training.**
  - No run edited a comment that states nothing.
  - No reply asked a question or refused.
  - The one run that moved the sort kept the sort's cost in the export. The request was
    about cost, so that run counts against the second change.
- **Cost.** v2 replies grew a little: Haiku 232 words (v1 215), Sonnet 215 (v1 196).
  Changed lines per run stayed about level: Haiku 12.3 (12.1), Sonnet 11.1 (9.3). Part of
  the Sonnet rise is the stale-comment fix v1 left out.

### Decision

No v3. Both changes moved the behaviour they targeted, and no graded check got worse. The
remaining move-into-consumer run is one run in three, and a further rule on three runs
per cell would be tuning to noise. The held-out pair ran next, on v2.

## Held-out cases

### What ran

- **The runs.** `heldout-haiku` (24 runs) and `heldout-sonnet` (16 runs) ran v2 and all
  four arms, on `first-wins-reason-in-caller` and `mention-without-constraint`. Haiku had
  3 runs per cell and Sonnet 2.
- **Run once, after the last edit.** The pair ran a single time, after the last skill
  edit, and no skill edit was informed by its results.
- **Exposure before the run.** No v2 edit drew on the pair: the v2 reviser made no tool
  call naming a held-out case. v1 was not written blind to it. The v1 writer read
  CASES.md, which then described both cases, and the build fixer made 10 tool calls
  naming a held-out case, read and edited their files, and in the same session made 7
  edits to SKILL.md before the gate ([README](../README.md) Limits).
- **Reads verified.** Every skill-arm run read its own snapshot before its first edit,
  and no run read the other arm's. No reminder or bare run read a snapshot. This rests
  on `verify-reads.json`, whose transcripts are not stored ([RESULTS.md](RESULTS.md),
  "Excluded runs").
- **No rulings, exclusions or reruns.** An auditor agent wrote no rulings, excluded no
  run and re-ran none. It left two Sonnet reply close calls unruled: a closing "Let me
  know if" or "Say if" sentence, in a reminder run and a shipped-skill run. Neither
  affects `with_skill`. [RESULTS.md](RESULTS.md) has the detail.

### Headline numbers (what the runs show)

| Model | Arm | Core | Preservation | Restraint | Reply | All checks |
| --- | --- | --- | --- | --- | --- | --- |
| Haiku | with_skill | 6/6 | 9/9 | 15/15 | 3/3 | 33/33 |
| Haiku | shipped_skill | 6/6 | 9/9 | 15/15 | 3/3 | 33/33 |
| Haiku | reminder | 6/6 | 9/9 | 14/15 | 3/3 | 32/33 |
| Haiku | without_skill | 6/6 | 9/9 | 15/15 | 3/3 | 33/33 |
| Sonnet | every arm | 4/4 | 6/6 | 10/10 | 2/2 | 22/22 |

The only failed check: Haiku reminder run-1 on `mention-without-constraint`. It added a
`round_price` line to `README.md`, which fails check 02.

### Per case (what the runs show)

#### `first-wins-reason-in-caller`

- **Every run of every arm passed all six checks.**
- **Every rewrite keeps the first login.** 18 used `setdefault`, and 2 (Haiku
  `with_skill`) used a dict comprehension over the reversed events. No run copied the
  last-wins `last_devices` comprehension the user suggested.
- **No run touched `billing/trial_clock.sql`.**
- **Every reply in every arm names `billing/trial_clock.sql`** (20/20). The bare model
  found the reason in a file no Python code reads, without help. That is the same ceiling
  the training cases showed.
- **Unscored: whether the reason went into the code.** The trial-clock reason went into
  the docstring or a comment in:
  - shipped_skill: 5/5;
  - reminder: 5/5;
  - with_skill: 3/5 (Haiku 1/3, Sonnet 2/2);
  - without_skill: 1/5.

  Every run stayed within check 05's three-line limit. The skill asks for no new
  comments, which may be why its runs leave the reason out more often than the arms that
  read the shipped skill or are told to "keep, or tell me about" constraints. That is an
  interpretation, not tested. 3/5 against 5/5 has p = 0.44.

#### `mention-without-constraint`

- **Every `with_skill` run passed all five checks.**
  - It added the `currency` argument and changed no file but `pricing/rounding.py` and
    its tests.
  - It added no defence and asked no question about callers.
- **What the restraint case was built to catch did not happen.** v2's new permission to
  edit other files, to fix text the change made false, could have spread into edits of
  descriptive mentions. No run did that.
- **Unscored: the replies reported a search that found nothing.**
  - Every `with_skill` reply (5/5) and every reminder reply (5/5) reports the search and
    lists the four files that mention `round_price`. Shipped-skill and bare replies
    report no search (0/5 each). Most still name the four callers as unaffected, and two
    bare Haiku replies (run-1, run-3) list all four files. The closest call is
    shipped-skill Sonnet run-2: it describes the callers' comments without reporting a
    search. So the line between the two is the writer's reading.
  - The skill's Report rule says to mention the sweep only when it changed the plan or
    found something stale, so `with_skill` broke its own rule here in every run.
  - Haiku `with_skill` run-2 also calls the four descriptive mentions "live" constraints,
    which mis-sorts them. That was harmless here, since no file changed.
  - Mean reply length, with_skill against bare and reminder:

    | Model | with_skill | bare | reminder |
    | --- | --- | --- | --- |
    | Haiku | 218 | 183 | 294 |
    | Sonnet | 162 | 148 | 217 |

    These are over both held-out cases.

### Does the skill generalise?

- **It did no harm on new material.** v2 scored 100% on both cases on both models. The
  restraint case found no over-reach from either v2 change.
- **It showed no gain to carry over.** The bare model, the shipped skill and the reminder
  also passed every core check. On core the held-out result is a tie with all three, and
  on all checks it is within one check of each. On first-wins, the only held-out case
  where the constraint lives in another file, the bare model was at ceiling. So this
  pair cannot test whether the skill's training behaviour generalises; it only shows
  that the skill does no harm on new material. Even that is material v1's authors had
  seen (Exposure, above), so it checks the v2 revision, not v1's rules blind.
- **The ungraded differences favour the other arms slightly.**
  - The reason went beside the code less often than with the shipped skill or the
    reminder.
  - The replies reported a search that changed nothing.

  Neither is established at 5 runs per arm.
- **The pair is spent.** It ran on v2 and cannot judge a later version.

### Limits of this evidence

- **Few runs.** 2 or 3 runs per cell, as in training.
- **Two held-out cases.** Only one of them (`first-wins-reason-in-caller`) needs evidence
  from another file. Neither case uses the dead-code or add-a-field request types, so
  the trigger's reach to new request types is tested only for "simplify".
- **No discovery data.** `discovery.py` was not run, so when each run found
  `trial_clock.sql` is inferred from its reply.
- **Hand counts.** The unscored counts above come from reading diffs and replies, not
  from a check.
