# change-drift-sweep: results

**Null result. The skill did not beat the one-line reminder or the shipped `code-comments`
skill, on either model, in training or on the held-out pair.** Every `with_skill` run
passed every check: 160/160 in iteration 1 (v1), 160/160 in iteration 2 (v2; two checks
passed by an auditor's ruling) and 60/60 held out. The other arms came close:
- the reminder scored 159/160 and 60/60;
- the shipped skill scored 159/160 and 59/60.

Each gap is one check in one run, which is noise at 2 or 3 runs per cell.

Its only clear margin is over the bare model on Haiku:
- **Training:** 96/96 against 88/96. All 15 skill runs passed every core check, against
  9 of 15 bare runs (two-sided Fisher p = 0.017, chosen after reading the runs).
- **Held out:** 36/36 against 34/36.

The reminder closes that gap as fully (96/96 and 36/36), and the shipped skill nearly so
(95/96 and 35/36). On Sonnet even the bare model scored 63/64 and 23/24.

The held-out case built to test generalisation, `poll-interval-average-wait`, did not trip
the skill. Every `with_skill` run found both averages derived by halving, a form SKILL.md
does not list. So did every reminder run and every shipped-skill run. The bare model left
one of them stale in 2 of 5 runs.

These are small samples: 2 or 3 runs per cell, seven small Python cases built by agents,
one model family. In every case a run could read the whole repository, so the search
step, and with it the script, had no room to show value. The reasoning is in
[ANALYSIS.md](ANALYSIS.md), the skill edits in [CHANGES.md](CHANGES.md), and case
selection in [GATE.md](GATE.md).

## What ran

Four arms, as the [incubator README](../../README.md) defines them:
- `with_skill` reads this skill's `SKILL.md` snapshot first, and may run
  `scripts/value_drift.py`.
- `shipped_skill` reads a snapshot of the shipped `code-comments` skill first. It does not
  get the `/code-comments:stale-refs` command.
- `reminder` gets the sentence in [arms.json](arms.json) added to the request: "After you
  change a value or a name, find every comment, docstring and doc that still states the
  old one, including number words, unit conversions and figures computed from it, and
  correct those that describe the current code, but leave changelog entries, ADRs, dated
  reports and outside facts word for word and report mismatches your change did not
  cause."
- `without_skill` gets the request alone.

Two models. Every run's transcript records `claude-haiku-5-5` or `claude-sonnet-5-5`, as
its iteration name says. The harness does not store the model id. Haiku ran 3 runs per
case per arm, and Sonnet 2.

| Iteration | Skill | Cases | Arms | Runs |
| --- | --- | --- | --- | --- |
| `gate-haiku`, `gate-sonnet` | none | all 7, before hardening | `without_skill` | 21, for case selection only, not counted ([GATE.md](GATE.md)) |
| `iteration-1-haiku` | v1 | 5 training | all 4 | 60 |
| `iteration-1-sonnet` | v1 | 5 training | all 4 | 40 |
| `iteration-2-haiku` | v2 | 5 training | `with_skill` only | 15 |
| `iteration-2-sonnet` | v2 | 5 training | `with_skill` only | 10 |
| `heldout-haiku` | v2 | 2 held out | all 4 | 24 |
| `heldout-sonnet` | v2 | 2 held out | all 4 | 16 |

This file counts 165 graded runs.

**Skill versions.** Each iteration keeps the files its runs read in `skill-snapshot/`:
- Both iteration-1 snapshots are v1 (SKILL.md, 106 lines), byte-identical to each other
  and to the committed v1.
- The iteration-2 and held-out snapshots are byte-identical to the current v2 (108
  lines).
- Every shipped-skill snapshot is byte-identical to
  `plugins/code-comments/skills/code-comments/`.

v2 made two changes ([CHANGES.md](CHANGES.md)):
1. The script reads a prose line together with the next line of the same block, so it
   finds a form that wraps across a line break.
2. SKILL.md says to search a value under 10 in a call of its own, because `--near` and
   `--unit` apply to every `--old` in a call.

**Iteration 2 is compared across runs.** It re-ran only `with_skill`. The other arms do
not read this skill, so v2 cannot change what they do. But their iteration-1 runs are a
separate sample from a separate run.

**How each run started.** Each agent read its task from `prompt.txt` as its first tool
call. A real request arrives as a user's message instead. The skill arms were told to
read the skill first.

**Skill reads.** Audit agents ran `verify-reads` on every iteration:
- Every skill-arm run read its snapshot SKILL.md before its first edit: iteration 1
  50/50 (53 counting the excluded originals), iteration 2 25/25, held out 20/20.
- In every skill-arm transcript, that read was the second tool call, right after
  `prompt.txt`. Sonnet often edited through Bash, which `verify-reads` does not count as
  an edit, but always after the skill read.
- No reminder or bare run read a skill snapshot.
- The `verify-reads` output was kept in the auditors' scratch folders, not in the
  iteration folders.

## Headline

Output of `python incubator/harness.py summary change-drift-sweep iteration-1-haiku
iteration-1-sonnet iteration-2-haiku iteration-2-sonnet heldout-haiku heldout-sonnet`.
Each cell gives the mean pass rate, then checks passed.

| Iteration | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` (v1) | 100.0%, 96/96 | 98.9%, 95/96 | 100.0%, 96/96 | 91.3%, 88/96 |
| `iteration-1-sonnet` (v1) | 100.0%, 64/64 | 100.0%, 64/64 | 98.3%, 63/64 | 98.6%, 63/64 |
| `iteration-2-haiku` (v2) | 100.0%, 96/96 | not run | not run | not run |
| `iteration-2-sonnet` (v2) | 100.0%, 64/64 | not run | not run | not run |
| `heldout-haiku` (v2) | 100.0%, 36/36 | 97.2%, 35/36 | 100.0%, 36/36 | 94.4%, 34/36 |
| `heldout-sonnet` (v2) | 100.0%, 24/24 | 100.0%, 24/24 | 100.0%, 24/24 | 95.8%, 23/24 |

Pass rate is the mean of each run's share of checks passed. That is why 63/64 gives
98.3% for the Sonnet reminder and 98.6% for bare Sonnet: their misses fall in cases
with 6 and 7 checks. The numbers include three rulings by auditor agents (see
"Rulings").

Pooled over both models:

| Split | Measure | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| Training, iteration 1 (v1) | all checks | 160/160 | 159/160 | 159/160 | 151/160 |
| | core | 100/100 | 100/100 | 99/100 | 92/100 |
| Training, iteration 2 (v2) | all checks | 160/160 | not run | not run | not run |
| | core | 100/100 | not run | not run | not run |
| Held out (v2) | all checks | 60/60 | 59/60 | 60/60 | 57/60 |
| | core | 30/30 | 29/30 | 30/30 | 27/30 |

## By focus

Checks passed with each `focus`, summed over runs. "No reply" counts runs without a
RESPONSE.md.

| Iteration | Arm | Core | Preservation | Restraint | Reply | No reply |
| --- | --- | --- | --- | --- | --- | --- |
| `iteration-1-haiku` | with_skill | 60/60 | 30/30 | 3/3 | 3/3 | 1 |
| | shipped_skill | 60/60 | 30/30 | 3/3 | 2/3 | 0 |
| | reminder | 60/60 | 30/30 | 3/3 | 3/3 | 1 |
| | without_skill | 53/60 | 29/30 | 3/3 | 3/3 | 0 |
| `iteration-1-sonnet` | with_skill | 40/40 | 20/20 | 2/2 | 2/2 | 0 |
| | shipped_skill | 40/40 | 20/20 | 2/2 | 2/2 | 0 |
| | reminder | 39/40 | 20/20 | 2/2 | 2/2 | 0 |
| | without_skill | 39/40 | 20/20 | 2/2 | 2/2 | 0 |
| `iteration-2-haiku` | with_skill | 60/60 | 30/30 | 3/3 | 3/3 | 0 |
| `iteration-2-sonnet` | with_skill | 40/40 | 20/20 | 2/2 | 2/2 | 0 |
| `heldout-haiku` | with_skill | 18/18 | 9/9 | 9/9 | - | 0 |
| | shipped_skill | 17/18 | 9/9 | 9/9 | - | 0 |
| | reminder | 18/18 | 9/9 | 9/9 | - | 0 |
| | without_skill | 16/18 | 9/9 | 9/9 | - | 0 |
| `heldout-sonnet` | with_skill | 12/12 | 6/6 | 6/6 | - | 0 |
| | shipped_skill | 12/12 | 6/6 | 6/6 | - | 0 |
| | reminder | 12/12 | 6/6 | 6/6 | - | 0 |
| | without_skill | 11/12 | 6/6 | 6/6 | - | 0 |

Reading the table:
- **The reply is graded by one check**, in `pre-existing-drift-reported`. Restraint is one
  check in training and three in the held-out pointer case. Neither held-out case grades
  the reply.
- **Two kept Haiku runs have no reply**: iteration-1 `with_skill` `default-value-drift`
  run 2 and `reminder` `unit-spelled-ttl` run 1. The run-limits guard blocked their
  Write of RESPONSE.md, and neither case grades the reply (see "Excluded runs").

## Per case

Checks passed per run.

### Training: iteration 1 (v1) and iteration 2 (v2)

| Case | Model | with_skill v1 | with_skill v2 | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- | --- |
| `default-value-drift` (of 7) | Haiku | 7, 7, 7 | 7, 7, 7 | 7, 7, 7 | 7, 7, 7 | 7, 7, 7 |
| | Sonnet | 7, 7 | 7, 7 | 7, 7 | 7, 7 | 7, **6** |
| `unit-spelled-ttl` (of 6) | Haiku | 6, 6, 6 | 6, 6, 6 | 6, 6, 6 | 6, 6, 6 | **4, 5, 5** |
| | Sonnet | 6, 6 | 6, 6 | 6, 6 | 6, **5** | 6, 6 |
| `derived-backoff-total` (of 6) | Haiku | 6, 6, 6 | 6, 6, 6 | 6, 6, 6 | 6, 6, 6 | 6, 6, 6 |
| | Sonnet | 6, 6 | 6, 6 | 6, 6 | 6, 6 | 6, 6 |
| `flag-rename-records-stay` (of 7) | Haiku | 7, 7, 7 | 7, 7, 7 | 7, 7, 7 | 7, 7, 7 | **6**, 7, 7 |
| | Sonnet | 7, 7 | 7, 7 | 7, 7 | 7, 7 | 7, 7 |
| `pre-existing-drift-reported` (of 6) | Haiku | 6, 6, 6 | 6, 6, 6 (one ruling) | 6, **5**, 6 | 6, 6, 6 | **5, 5, 5** |
| | Sonnet | 6, 6 | 6, 6 (one ruling) | 6, 6 | 6, 6 | 6, 6 |

Every failed check, after rulings:
- **Bare Haiku, `unit-spelled-ttl`, check 02 in all 3 runs.**
  - Runs 2 and 3 left the wrapped "a quarter of an hour" in the `auth/forms.py`
    docstring.
  - Run 1 left "fifteen minutes" in `auth/views.py` and "After 14 minutes" in
    `docs/console.md`, so it also failed check 03.
- **Bare Haiku, `pre-existing-drift-reported`, check 02 in all 3 runs.** Each left "at
  most 2,000 notifications a second" in the `notify/sender.py` docstring, and run 3 also
  left "costs 10 calls" in `docs/billing.md`.
- **Bare Haiku, `flag-rename-records-stay` run 1, check 05.** It added a note line to
  the accepted ADR 0002, a record.
- **Shipped Haiku, `pre-existing-drift-reported` run 2, the reply check.** The reply
  never mentions the flush mismatch.
- **Reminder Sonnet, `unit-spelled-ttl` run 2, check 02.** It left "fifteen minutes" in
  the `auth/views.py` docstring.
- **Bare Sonnet, `default-value-drift` run 2, check 02.** It left "fifty at a time" in
  the `exporter/sync.py` docstring, the same miss the gate's Sonnet run made.

What the training cases show:
- **Two hardened cases gave bare Haiku headroom:** `unit-spelled-ttl` and
  `pre-existing-drift-reported`, 0 of 3 bare runs with full core in each.
- **The other two hardened cases gave none.** `derived-backoff-total` is at ceiling for
  every arm on both models, and `flag-rename-records-stay` is at ceiling on core.
- **Bare Sonnet passed every hardened case.**
- **No case separated the skill from the reminder or the shipped skill.** Their only
  misses were one reply on Haiku (shipped) and one docstring on Sonnet (reminder).

### Held out (v2)

| Case | Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| `pointer-comment-needs-nothing` (of 6) | Haiku | 6, 6, 6 | 6, 6, 6 | 6, 6, 6 | 6, 6, 6 |
| | Sonnet | 6, 6 | 6, 6 | 6, 6 | 6, 6 |
| `poll-interval-average-wait` (of 6) | Haiku | 6, 6, 6 | 6, 6, **5** | 6, 6, 6 | **5, 5**, 6 |
| | Sonnet | 6, 6 | 6, 6 | 6, 6 | **5**, 6 |

Every held-out failure is check 02 of `poll-interval-average-wait`:
- **Stale average left.** Bare Haiku run 2 and bare Sonnet run 1 left "An order has
  already waited about 150 s on average" in the `orders/queue.py` docstring.
- **Ambiguous gloss.** Bare Haiku run 1 and shipped Haiku run 3 wrote, in
  `docs/fulfilment.md`: "on average five minutes after the storefront lists it, since the
  poller picks it up half a poll interval (ten minutes) later on average."
  - The check reads "(ten minutes)" as 600 s in a sentence about the average wait.
  - The parenthesis may gloss "a poll interval", which would be true. The auditor
    found no reply that settles it, so no ruling was made.
  - `test_grade.py` has no variant for this wording.

## Held-out cases: does the skill generalise?

The held-out pair is the main test of whether the skill works beyond the cases it was
revised on. No skill edit drew on these cases. They ran once, on v2, after the last
edit.

| Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| Haiku (6 runs per arm) | 100.0%, 36/36, core 18/18 | 97.2%, 35/36, core 17/18 | 100.0%, 36/36, core 18/18 | 94.4%, 34/36, core 16/18 |
| Sonnet (4 runs per arm) | 100.0%, 24/24, core 12/12 | 100.0%, 24/24, core 12/12 | 100.0%, 24/24, core 12/12 | 95.8%, 23/24, core 11/12 |

**`poll-interval-average-wait`: the generalisation check.** It tests two things SKILL.md
does not name:
- a figure derived by halving the old value (an average wait);
- a dated record that sits as a section of a living page.

What the runs show:
- **Derived by halving.** All 5 `with_skill` runs corrected both averages: the
  `docs/fulfilment.md` sentence and the `orders/queue.py` docstring, which never names
  `POLL_INTERVAL_S`.
  - The 3 Haiku runs each worked out the halved figure (150 s, 2.5 min, "two and a half
    minutes") and passed it to the script in their first call. That is the skill's
    derived-figure step applied to a form it does not list.
  - The script then listed the queue docstring's "about 150 s" in all three. It listed
    the fulfilment sentence only in the run that passed "two and a half minutes" as
    literal text. HELD-OUT.md predicted this gap.
  - Each Haiku run had printed every file before its first script call.
  - The 2 Sonnet runs did not run the script. Run 1 printed every file. Run 2 grepped for
    the old forms, 150 among them, and opened the files they named.
- **The other arms did as well, except the bare model.**
  - Reminder: 5/5 runs, with the same five edits as the skill.
  - Shipped skill: 5/5 corrected both averages; Haiku run 3 failed on the gloss above.
  - Bare model: 2 of 5 runs left the queue docstring stale, and 1 more wrote the gloss.
  - With the skill against bare: 5/5 against 2/5 full marks (Fisher p = 0.17).
- **The record inside a living page held in every arm.** No run in any arm changed the
  dated "Past incidents" entry, the storefront's cache and quota, or the packers' five
  minutes (20/20 on check 04).

**`pointer-comment-needs-nothing`: the restraint guard.**
- All 20 runs passed every check.
- Every `with_skill` run changed only `MAX_PARALLEL = 8`, as did every shipped-skill and
  reminder run.
- The script's lists for `--old 4` held only lines to leave:
  - the "tried four times" retry count;
  - the four-second dashboard refresh;
  - the pointer comments, in the runs that also passed `MAX_PARALLEL`;
  - a CHANGELOG entry and a dated report, both marked `record?`.

  Every skill run left them all.
- 4 of 5 bare runs (3 Haiku, 1 Sonnet) also added a new `## Unreleased` CHANGELOG section
  with "Jobs run up to 8 at a time instead of 4." The graders allow that.
- So the skill did not cause over-editing. That is the risk this case was built to catch.

**Interpretation.** On new material the skill did no harm and missed nothing. Its
derived-figure step reached a form it does not list. But the reminder sentence, which
names "figures computed from it", got the same result in every run. So did the shipped
skill on the figures themselves. The held-out pair confirms the training result: a tie
with the reminder and the shipped skill, and a small, noisy lead over the bare model.

## Iteration 2: did the v2 changes work?

v2 could not raise a graded result, because v1 was already at 160/160. Iteration 2 checks
that v2 did no harm and that each change hit its target. These are `with_skill` runs, 15
Haiku and 10 Sonnet.

| v2 change | Target in iteration 1 | v1 | v2 | Read |
| --- | --- | --- | --- | --- |
| 1. Read a line with the next line of its block | The wrapped quarter-hour idiom in the `auth/forms.py` docstring, `unit-spelled-ttl`, Haiku | left out of the list in 3/3 runs | listed in 2/2 runs that ran the script before editing; run 2 ran it only after its edits | **Fixed on this case.** The first call listed 10 lines in 7 files, against 9 in 6 for v1 with similar arguments. After the edit, run 3's list marked the wrapped "half an hour" `states new`. |
| 2. A value under 10 gets a call of its own | One Haiku run's `--near` dropped a derived-figure line | 1/15 runs | `--near` used in 4/15 Haiku and 2/10 Sonnet runs | **Not testable here.** In `derived-backoff-total`, Haiku runs 1 and 3 each still put `--near` on a call that also held the derived figures. Run 3 had first searched the 4 in a call of its own, as v2 asks. Every run read every file and passed every check, so a dropped hit would cost nothing. |

What else iteration 2 shows:
- **Scores held:** 96/96 on Haiku and 64/64 on Sonnet, the same as v1.
- **Two reply checks were ruled to pass.** Haiku run 3 and Sonnet run 1 of
  `pre-existing-drift-reported` reported the flush mismatch with both values. They said
  "This was already false" or "Drift that was already there", and the reply check's
  contrast list has neither word. SKILL.md itself uses both words ("A sentence already
  false before your change", "Drift your change did not cause"). Before the rulings v2
  scored 95/96 and 63/64.
- **Sonnet corrected the pre-existing drift in 2/2 runs.** Both changed the flush sentence
  to 30 seconds, toward the code. Run 2 also changed "a minute" to "half a minute".
  Check 03 accepted both. No run in any arm made this correction in iteration 1. Haiku
  v2 left the sentence and reported it, as v1 did. SKILL.md allows both.
- **Sonnet ran the script in 2/10 runs**, both in `default-value-drift`, against 0/10
  in v1. Haiku ran it in 15/15, as before.
- **One Haiku run renamed the internal `since` parameter**, which the request did not
  ask for (`flag-rename-records-stay` run 1). No v1 skill run did this; one bare and one
  reminder run did in iteration 1. No check grades it.
- **No arithmetic went into the `derived-backoff-total` docstrings.** One v1 run had
  written "(40 x 31 s = 1,240 s)".
- **Replies did not get shorter.** v2 left the reply rules alone. Haiku replies averaged
  245 words (v1: 228), Sonnet 234 (v1: 245).

## The script, `value_drift.py`

| Iteration | Haiku `with_skill` runs that ran it | Sonnet `with_skill` runs that ran it |
| --- | --- | --- |
| iteration 1 (v1) | 15/15 | 0/10 |
| iteration 2 (v2) | 15/15 | 2/10 |
| held out (v2) | 6/6 | 2/4 (pointer case only) |

No other arm ran it. What the runs show:
- **It never was the only route to a fix.** The iteration-1 auditor traced every
  iteration-1 run, and the writer traced the iteration-2 `unit-spelled-ttl` runs and the
  held-out runs. Each run had printed every relevant file before its first script call or
  in the same command, or it ran the script only after editing. The script served as a
  checklist and a final check.
- **It did not flood.** Calls made before any edit listed 2 to 12 prose lines in 2 to 9
  files. Every line that was not a living description was one of these:
  - a record, with or without the `record?` hint;
  - an outside fact;
  - a lure that shares the number;
  - a pointer the run had itself passed as `--old`;
  - one Markdown step number.

  No run edited any of them.
- **Known gap confirmed held out.** "two and a half minutes" is not matched from 150 s or
  2.5 min. A run that did not read the file would have missed it.
- **Sonnet mostly skips it.** Reading the whole repository was cheaper.

The fixtures have 9 to 13 files, so reading everything is always possible. The script's
recall cannot matter until a case is too large to read whole.

## Rulings (overrides) by arm

Every ruling was made by an auditor agent, not a human. Each sits in that run's
`overrides.json`, and the check's own result stays in the evidence. All three turned a
heuristic fail into a pass.

| Iteration | with_skill | shipped_skill | reminder | without_skill | Total |
| --- | --- | --- | --- | --- | --- |
| `iteration-1-haiku` | 0 | 1 to pass | 0 | 0 | 1 |
| `iteration-1-sonnet` | 0 | 0 | 0 | 0 | 0 |
| `iteration-2-haiku` | 1 to pass | not run | not run | not run | 1 |
| `iteration-2-sonnet` | 1 to pass | not run | not run | not run | 1 |
| `heldout-haiku` | 0 | 0 | 0 | 0 | 0 |
| `heldout-sonnet` | 0 | 0 | 0 | 0 | 0 |
| **Net checks** | **+2** | **+1** | **0** | **0** | 3 |

The rulings:
- **Shipped Haiku, `default-value-drift` run 3, check 02.** The run wrote "The API
  rejects requests above 500 rows (docs/limits.md)" beside the constant. 500 is the
  ledger team's limit, not a page size. The check's limit exclusion knows "more than",
  "over" and "up to", but not "above".
- **v2 Haiku run 3 and Sonnet run 1, `pre-existing-drift-reported`, the reply check.**
  Each reply had the cues for the flush, 60 and 30 in one paragraph. The check failed it
  only for a missing contrast word, as described under Iteration 2.

On the checks' own results, before any ruling, only three cells change:
- `iteration-1-haiku` shipped_skill: 97.9% (94/96);
- `iteration-2-haiku` with_skill: 98.9% (95/96);
- `iteration-2-sonnet` with_skill: 98.3% (63/64).

Without the rulings, v2 would trail v1 by one check on each model. That would be a grader
artefact: the reply check misses the skill's own words.

**No grader bug was recorded:** no check was wrong for every run. Three heuristic gaps
remain in `eval/grade.py`:
- `_C1_LIMIT_BEFORE` lacks "above";
- `_C5_CONTRAST` lacks "false" and "drift", which SKILL.md's own wording leads to;
- the poll case's check 02 has no variant for the "(ten minutes)" gloss.

## Excluded runs

Four iteration-1 runs were excluded and re-run, all for the same environment fault: the
run-limits guard misread the agent's shell command. The originals are kept in
`iterations/<iteration>/excluded-runs/`, each with an `EXCLUDED.txt`.

| Run | What the guard blocked | Original, graded in memory | Replacement |
| --- | --- | --- | --- |
| Sonnet `default-value-drift` `shipped_skill` run 2 | its first `sed -i` with a heredoc | 4/7, no changes, no reply | 7/7 |
| Sonnet `unit-spelled-ttl` `reminder` run 1 | its first `sed -i` with a heredoc | 3/6, no changes, no reply | 6/6 |
| Sonnet `unit-spelled-ttl` `with_skill` run 1 | its first `sed -i` with a heredoc | 3/6, no changes, no reply | 6/6 |
| Haiku `pre-existing-drift-reported` `shipped_skill` run 3 | the heredoc writing RESPONSE.md; it read "up to 250." after a `>` as a file name | 5/6: edits done, reply check failed | 6/6 |

With the Haiku original, the shipped skill would score 94/96 on iteration-1 Haiku instead
of 95/96. The three Sonnet originals made no edit at all.

Two more Haiku runs were kept without a reply:
- iteration-1 `with_skill` `default-value-drift` run 2;
- `reminder` `unit-spelled-ttl` run 1.

The guard blocked their Write of RESPONSE.md to a path spelled `/tmp/...`. Their cases
grade no reply, and all their edits were graded (7/7 and 6/6). No iteration-2 or held-out
run was excluded.

## What with_skill did that the others did not

- **It never failed a graded check:** 380/380 over 25 v1, 25 v2 and 10 held-out runs,
  with two rulings in its favour. No other arm went without a miss. But the reminder's
  single miss and the shipped skill's two are one run each.
- **It never created a changelog section.** In `default-value-drift`, which has no
  `Unreleased` heading, it added none in 10/10 runs over v1 and v2. The bare model added
  one in 5/5 runs and the shipped skill in 2/5. In the held-out pointer case it added
  none in 5/5, against 4/5 for the bare model. The reminder also added none in either
  case, so this is a gain over the bare model and the shipped skill only. No check
  grades it.
- **It added no comment beside the constant.** The shipped skill added or extended a
  rationale or limit comment there in four cases:
  - `default-value-drift`: 4 of 5 runs, each citing the ledger's 500-row limit;
  - `pre-existing-drift-reported`: 3 of 5 runs, all on Haiku, about the per-call bill;
  - `derived-backoff-total`: 2 of 5 runs, both on Haiku;
  - held-out `poll-interval-average-wait`: 5 of 5 runs, 4 of them restating "Ten
    minutes".

  No `with_skill`, reminder or bare run changed a comment at the constant. The graders
  allow these comments.
- **It kept the sentence's word form on Haiku.** In `pre-existing-drift-reported` the
  README said "a hundred at a time". Haiku wrote "two hundred and fifty at a time" in 6/6
  skill runs over v1 and v2. The reminder did so in 2/3, and the shipped skill and the
  bare model used digits in 3/3. Sonnet used digits in every arm. Ungraded.
- **It restated the new figure rather than pointing to the constant**, in nearly every
  corrected line. The shipped skill pointed to the constant more often. Both pass.
- **On Haiku it ran `value_drift.py` in every run.** No other arm had the script. It
  found nothing that reading had not.
- **v2 on Sonnet corrected the pre-existing flush figure toward the code** in 2/2 runs.
  No other run of any arm did. The other arms ran only in iteration 1, so this compares
  separate samples.

## What the others did that with_skill did not

- **The reminder matched it on every graded check on Haiku** (96/96 training, 36/36 held
  out), with shorter replies and fewer tool calls. Its one miss was one Sonnet docstring.
- **The shipped skill matched it on Sonnet** (64/64 training, 24/24 held out). Its
  Haiku misses were one reply that omitted the flush mismatch and one ambiguous gloss.
- **The bare Sonnet model nearly matched it** (63/64, 23/24). It is the cheapest arm on
  Sonnet training.
- **Every other arm wrote shorter replies.** The skill's replies were the longest in
  every iteration and on both models (see "Cost"). Part of the extra is sentences that
  report an empty category. The reminder wrote these too.
- **The shipped skill pointed to the constant** ("PAGE_SIZE rows per request") more
  often. That is a correction SKILL.md also allows, and one that does not drift again.

## Cost

Means per graded run. Tool calls are counted once each, by id, from the assistant
messages. Output tokens are counted once per API message. Words are whitespace-separated
tokens in RESPONSE.md, over the runs that have one.

| Iteration | Arm | Reply words, mean (median) | Tool calls | Output tokens |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` | with_skill | 228 (232) | 19.7 | 7.7k |
| | shipped_skill | 197 (203) | 14.9 | 6.0k |
| | reminder | 208 (198) | 15.4 | 6.1k |
| | without_skill | 186 (174) | 17.1 | 5.3k |
| `iteration-1-sonnet` | with_skill | 245 (246) | 7.5 | 2.9k |
| | shipped_skill | 219 (218) | 7.5 | 2.8k |
| | reminder | 199 (214) | 5.6 | 2.3k |
| | without_skill | 169 (186) | 4.8 | 2.0k |
| `iteration-2-haiku` | with_skill | 245 (257) | 17.9 | 7.5k |
| `iteration-2-sonnet` | with_skill | 234 (222) | 8.1 | 3.0k |
| `heldout-haiku` | with_skill | 222 (230) | 15.3 | 5.9k |
| | shipped_skill | 180 (192) | 12.2 | 4.9k |
| | reminder | 201 (196) | 14.5 | 5.2k |
| | without_skill | 136 (126) | 12.7 | 3.7k |
| `heldout-sonnet` | with_skill | 212 (204) | 5.8 | 2.1k |
| | shipped_skill | 157 (150) | 5.0 | 1.9k |
| | reminder | 178 (179) | 3.5 | 1.5k |
| | without_skill | 169 (168) | 7.5 | 2.4k |

What the table shows:
- **Replies.** The skill's were the longest in every iteration. Held out, they ran 1.1
  to 1.2 times the reminder's length, and 1.25 to 1.6 times the bare model's.
- **Tool calls and tokens.** On Haiku the skill spent the most in every iteration. On
  Sonnet it was close to the shipped skill, and held out the bare model spent more than
  either.
- **Failed edits.** In iteration 1, 26% to 41% of each Haiku arm's Edit calls failed
  with "File has not been read yet", an Edit sent before the file was opened with Read.
  Every Haiku Edit error in these runs was of that kind, so retries raise the Haiku tool
  counts in every arm.

## Where the numbers come from

- Pass rates, checks and focus counts come from each iteration's `benchmark.json`, which
  `harness.py grade` writes after the audits.
- Before-ruling figures come from each ruling's "check said" evidence.
- Transcripts are matched to runs by the outputs path in their first message, which is
  how `verify-reads` matches them. Where a run was re-run, the later transcript is used.
- Tool calls, tokens, script use and Edit errors were counted by the writer from the
  transcripts.
  - Each transcript also stores copies of earlier messages in its request records.
    Counting those copies roughly doubles the tool counts.
  - `harness.py verify-reads` counts them too, so its `tool_calls` field runs high.
- Changelog, comment, word-form and parameter-rename counts come from each run's
  `changes.diff`. They are ungraded.
- The originals of excluded runs were graded in memory with `harness.grade`, and nothing
  was written.
- Fisher exact p-values are two-sided, for comparisons chosen after reading the runs.
