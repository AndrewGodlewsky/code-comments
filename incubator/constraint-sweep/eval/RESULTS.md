# constraint-sweep: results

**On graded checks, the skill shows no reliable gain over the one-line reminder or the
bare model on either model, in training or on the held-out pair.** It ties them on core
checks. In iteration 1 its all-checks leads are one or two checks, inside run-to-run
variation. v2 is compared with the other arms' iteration-1 runs, a separate sample. It
leads by 6 checks on Haiku (94/96 against 88/96 for the reminder and the bare model) and
by 2 or 3 on Sonnet (64/64 against 62/64 and 61/64). Against the reminder on Haiku, 4 of
those 6 are sort checks 04 and 07, which v2 failed in 1/3 runs and the reminder in 3/3
(p = 0.40). So these leads are not established either. It beat the shipped
`code-comments` skill only on the training cases, because the shipped skill broke a
constraint it had found in 6 of 25 iteration-1 runs. On the held-out pair all four arms
tie on core.

The bare model passed every core check it was given: 25 of 25 in training and 10 of 10
held out. So the eval never tested the skill's main claim, that it stops a change from
breaking a constraint stated only in another file, in a setting where the bare model
fails.

The clearest difference between arms is not graded. On the positional pair the skill put
the new column where the user asked and changed the positional load in step in 10 of 10
runs. The reminder did this in 3 of 10 runs and the bare model in 0 of 10; their other
runs appended the column at the end and said why. The graders accept both outcomes.

These are small samples: 2 or 3 runs per cell, seven small Python cases built by agents,
one model family. The reasoning behind each number is in [ANALYSIS.md](ANALYSIS.md), the
skill edits are in [CHANGES.md](CHANGES.md), and case selection is in [GATE.md](GATE.md).

## What ran

Four arms, as the [incubator README](../../README.md) defines them:
- `with_skill` reads this skill's `SKILL.md` snapshot first.
- `shipped_skill` reads a snapshot of the shipped `code-comments` skill first.
- `reminder` gets the sentence in [arms.json](arms.json) added to the request: "Before you
  change what existing code returns, orders, accepts or removes, grep the whole repository
  (every file type, not only Python importers) for the names you are changing, and keep,
  or tell me about, any constraint that comments, docstrings or tests there state."
- `without_skill` gets the request alone.

Two models: Claude Haiku and Claude Sonnet. Haiku ran 3 runs per case per arm, Sonnet 2.

| Iteration | Skill | Cases | Arms | Runs |
| --- | --- | --- | --- | --- |
| `gate-haiku`, `gate-sonnet` | none | all 7, before hardening | `without_skill` | 21, used for case selection only, not counted ([GATE.md](GATE.md)) |
| `iteration-1-haiku` | v1 | 5 training | all 4 | 60 |
| `iteration-1-sonnet` | v1 | 5 training | all 4 | 40 |
| `iteration-2-haiku` | v2 | 5 training | `with_skill` only | 15 |
| `iteration-2-sonnet` | v2 | 5 training | `with_skill` only | 10 |
| `heldout-haiku` | v2 | 2 held out | all 4 | 24 |
| `heldout-sonnet` | v2 | 2 held out | all 4 | 16 |

This file counts 165 graded runs. Each iteration keeps its `SKILL.md` in `skill-snapshot/`:
- The iteration-1 snapshot is v1, with a 94-line body.
- The iteration-2 and held-out snapshots are byte-identical to the current v2, with a
  103-line body.
- The shipped-skill snapshot is byte-identical to
  `plugins/code-comments/skills/code-comments/SKILL.md`.

v2 changed two rules ([CHANGES.md](CHANGES.md)):
- Text the change makes false is corrected in the same change.
- Moving the work into a dependent does not count as keeping the property where it is
  produced.

Iteration 2 re-ran only `with_skill`, so v2 is compared with the other arms' iteration-1
runs. Those arms do not read this skill, so the edit cannot change what they do. But
they are separate samples from a separate run.

Each agent read its task from `prompt.txt` as its first tool call. A real request arrives
as a user's message instead.

## Headline

From `python incubator/harness.py summary constraint-sweep iteration-1-haiku
iteration-1-sonnet iteration-2-haiku iteration-2-sonnet heldout-haiku heldout-sonnet`:

| Iteration | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `iteration-1-haiku` (v1) | 94.3%, 90/96 | 85.7%, 81/96 | 92.4%, 88/96 | 92.4%, 88/96 |
| `iteration-1-sonnet` (v1) | 98.6%, 63/64 | 94.3%, 60/64 | 97.1%, 62/64 | 95.7%, 61/64 |
| `iteration-2-haiku` (v2) | 98.1%, 94/96 | not run | not run | not run |
| `iteration-2-sonnet` (v2) | 100.0%, 64/64 | not run | not run | not run |
| `heldout-haiku` (v2) | 100.0%, 33/33 | 100.0%, 33/33 | 96.7%, 32/33 | 100.0%, 33/33 |
| `heldout-sonnet` (v2) | 100.0%, 22/22 | 100.0%, 22/22 | 100.0%, 22/22 | 100.0%, 22/22 |

Pass rate is the mean of each run's share of checks passed. Every run in every arm wrote a
reply: the benchmark's "No reply" column is 0 throughout. No ruling changed any number
(see "Rulings").

## By focus

Checks passed, summed over runs, from each iteration's `benchmark.json`.

| Iteration | Arm | Core | Preservation | Restraint | Reply |
| --- | --- | --- | --- | --- | --- |
| `iteration-1-haiku` | with_skill | 15/15 | 27/30 | 33/36 | 15/15 |
| | shipped_skill | **10/15** | 27/30 | 34/36 | 10/15 |
| | reminder | 15/15 | 27/30 | 31/36 | 15/15 |
| | without_skill | 15/15 | 28/30 | 30/36 | 15/15 |
| `iteration-1-sonnet` | with_skill | 10/10 | 20/20 | 23/24 | 10/10 |
| | shipped_skill | **9/10** | 19/20 | 23/24 | 9/10 |
| | reminder | 10/10 | 19/20 | 23/24 | 10/10 |
| | without_skill | 10/10 | 19/20 | 22/24 | 10/10 |
| `iteration-2-haiku` | with_skill | 15/15 | 29/30 | 35/36 | 15/15 |
| `iteration-2-sonnet` | with_skill | 10/10 | 20/20 | 24/24 | 10/10 |
| `heldout-haiku` | with_skill | 6/6 | 9/9 | 15/15 | 3/3 |
| | shipped_skill | 6/6 | 9/9 | 15/15 | 3/3 |
| | reminder | 6/6 | 9/9 | 14/15 | 3/3 |
| | without_skill | 6/6 | 9/9 | 15/15 | 3/3 |
| `heldout-sonnet` | with_skill | 4/4 | 6/6 | 10/10 | 2/2 |
| | shipped_skill | 4/4 | 6/6 | 10/10 | 2/2 |
| | reminder | 4/4 | 6/6 | 10/10 | 2/2 |
| | without_skill | 4/4 | 6/6 | 10/10 | 2/2 |

How to read the table:
- **Core** is one hidden-test check per case. Over both models, every arm except
  `shipped_skill` passed every core check in every iteration. `shipped_skill` passed
  19/25 in training.
- **Reply** checks are keyword heuristics. The sort and positional reply checks (06) are
  scored only when core passes, so a core failure also costs a reply check.
  `shipped_skill`'s six iteration-1 reply failures are its six core failures.
- **The held-out reply column** comes from `mention-without-constraint` alone. The
  first-wins case has no reply check.

## Per case

Checks passed per run, from each iteration's `benchmark.md`.

`iteration-1-haiku` (v1):

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `dispatched-by-name` | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 |
| `positional-columns-in-sql` | 7/7, 7/7, 7/7 | 7/7, 5/7, 5/7 | 6/7, 7/7, 7/7 | 7/7, 6/7, 6/7 |
| `positional-columns-in-sql-pointer` | 7/7, 7/7, 7/7 | 7/7, 5/7, 7/7 | 7/7, 7/7, 6/7 | 7/7, 7/7, 6/7 |
| `sort-relied-on-elsewhere` | 5/7, 5/7, 5/7 | 3/7, 5/7, 4/7 | 5/7, 5/7, 5/7 | 5/7, 6/7, 5/7 |
| `stale-constraint-elsewhere` | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 |

`iteration-1-sonnet` (v1):

| Case | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| `dispatched-by-name` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| `positional-columns-in-sql` | 7/7, 6/7 | 7/7, 7/7 | 7/7, 7/7 | 7/7, 7/7 |
| `positional-columns-in-sql-pointer` | 7/7, 7/7 | 7/7, 6/7 | 7/7, 7/7 | 7/7, 6/7 |
| `sort-relied-on-elsewhere` | 7/7, 7/7 | 4/7, 7/7 | 5/7, 7/7 | 5/7, 7/7 |
| `stale-constraint-elsewhere` | 5/5, 5/5 | 5/5, 5/5 | 5/5, 5/5 | 5/5, 5/5 |

`iteration-2-haiku` and `iteration-2-sonnet` (v2, `with_skill` only):

| Case | Haiku | Sonnet |
| --- | --- | --- |
| `dispatched-by-name` | 6/6, 6/6, 6/6 | 6/6, 6/6 |
| `positional-columns-in-sql` | 7/7, 7/7, 7/7 | 7/7, 7/7 |
| `positional-columns-in-sql-pointer` | 7/7, 7/7, 7/7 | 7/7, 7/7 |
| `sort-relied-on-elsewhere` | 5/7, 7/7, 7/7 | 7/7, 7/7 |
| `stale-constraint-elsewhere` | 5/5, 5/5, 5/5 | 5/5, 5/5 |

`heldout-haiku` and `heldout-sonnet` (v2):

| Case | Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| `first-wins-reason-in-caller` | Haiku | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 | 6/6, 6/6, 6/6 |
| `first-wins-reason-in-caller` | Sonnet | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| `mention-without-constraint` | Haiku | 5/5, 5/5, 5/5 | 5/5, 5/5, 5/5 | 4/5, 5/5, 5/5 | 5/5, 5/5, 5/5 |
| `mention-without-constraint` | Sonnet | 5/5, 5/5 | 5/5, 5/5 | 5/5, 5/5 | 5/5, 5/5 |

`dispatched-by-name` and `stale-constraint-elsewhere` sit at ceiling for every arm in
every iteration, so on graded checks they cannot separate arms.

### The checks that separated arms

Iteration 1, Haiku and Sonnet together, 5 runs per arm in each case. Every check not
listed passed in every run of every arm.

| Case: check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| sort 01, hidden tests: export in id order (core) | 5/5 | **2/5** | 5/5 | 5/5 |
| sort 02, Python sort removed (restraint) | 5/5 | 5/5 | 5/5 | 4/5 |
| sort 04, upload script's comment lines kept (preservation) | 2/5 (Haiku 0/3) | 1/5 | 1/5 | 2/5 |
| sort 06, reply names the upload (reply) | 5/5 | 2/5 | 5/5 | 5/5 |
| sort 07, files only read are untouched (restraint) | 2/5 (Haiku 0/3) | 3/5 | 1/5 | 2/5 |
| positional 01, hidden tests: warehouse load intact (core) | 5/5 | **3/5** | 5/5 | 5/5 |
| positional 06, reply names the load (reply) | 5/5 | 3/5 | 5/5 | 5/5 |
| positional 07, files only read are untouched (restraint) | 4/5 | 5/5 | 4/5 | 3/5 |
| pointer 01, hidden tests: warehouse load intact (core) | 5/5 | **4/5** | 5/5 | 5/5 |
| pointer 06, reply names the load (reply) | 5/5 | 4/5 | 5/5 | 5/5 |
| pointer 07, files only read are untouched (restraint) | 5/5 | 4/5 | 4/5 | 3/5 |

How each failure came about:
- **Sort 04 and 07 fail together.** A run that moves the Python sort into the export path
  edits `ledger/nightly.py` (07). It also rewrites the upload script's comment, which named
  `fetch_rows` as the source of the order (04).
- **Positional 07 and pointer 07** are edits nobody asked for to `docs/finance.md`
  describing the new column.

After v2, the only failed checks in iteration 2 were sort 04 and 07 in one Haiku run (4/5
each over both models). On the held-out pair the only failed check was
`mention-without-constraint` 02 in one Haiku reminder run, which edited `README.md`.

## Ungraded behaviours that separated arms

The writer of this file counted these from each run's `changes.diff`, `RESPONSE.md` and
`outputs/`. They are not graded and not in the benchmark. The p-values are two-sided Fisher
exact tests on comparisons chosen after reading the runs, so read them as descriptive.

| Behaviour | with_skill v1 | with_skill v2 | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| Positional pair: column next to amount, as asked, and the load renumbered in step | **10/10** | **10/10** | 2/10 | 3/10 | 0/10 |
| Positional pair: column next to amount, load left alone (the load breaks) | 0/10 | 0/10 | 3/10 | 0/10 | 0/10 |
| Positional pair: column appended at the end, and the reply names the load | 0/10 | 0/10 | 5/10 | 7/10 | 10/10 |
| Sort: order kept at the producer (`ORDER BY id` in the query) | 2/5 (Sonnet 2/2) | 4/5 (Haiku 2/3) | 1/5 | 1/5 | 1/5 |
| Sort: Python sort moved into the export path | 3/5 (Haiku 3/3) | 1/5 (Haiku 1/3) | 1/5 | 4/5 | 3/5 |
| Sort: sort dropped and the order lost | 0/5 | 0/5 | 3/5 | 0/5 | 0/5 |
| Sort: nothing changed, the user asked to choose | 0/5 | 0/5 | 0/5 | 0/5 | 1/5 |
| Stale case: comment the change made false left in place, only reported | **5/5** | 0/5 | 0/5 | 0/5 | 0/5 |
| Held out, first-wins: the trial-clock reason written into the code | not run | 3/5 | 5/5 | 5/5 | 1/5 |
| Held out, restraint case: reply reports the search although it changed nothing | not run | 5/5 | 0/5 | 5/5 | 0/5 |

What the p-values say:
- **Named form kept.** with_skill v1 against the reminder is 10/10 against 3/10
  (p = 0.003). Against the shipped skill p = 0.0007, and against the bare model
  p = 0.00001. v2 repeated v1's 10/10.
- **Stale comment.** v1 left the false comment in 5/5 runs against 0/15 in the other arms
  (p = 0.00006). v2 corrected it in 5/5, against v1's 0/5 (p = 0.008).
- **Sort fix kept at the producer.** v2 against v1 is 4/5 against 2/5 (p = 0.52). On
  Haiku alone it is 2/3 against 0/3 (p = 0.40). v2 is in the expected direction, but the
  gain is not established.
- **Held-out first-wins.** with_skill against the shipped skill or the reminder is 3/5
  against 5/5 (p = 0.44).

## Held-out cases: does the skill generalise?

The held-out pair was meant as the main test of whether rules tuned on the training cases
carry over to new material. No v2 edit looked at it. It ran once, on v2, after the last
edit. The bare gate did run on both cases, before `first-wins-reason-in-caller` was
hardened. Gate runs decide no skill edit ([GATE.md](GATE.md)). But v1 was not written
blind to the pair. The v1 writer read CASES.md, which then described both cases. The
build fixer read and edited their files and, in the same session, made 7 edits to
SKILL.md ([README](../README.md) Limits). So the pair guards the v2 revision against
overfitting; it is not a blind test of v1's rules.

| Case: check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| first-wins 01, hidden tests: each trial starts at the first login (core) | 5/5 | 5/5 | 5/5 | 5/5 |
| first-wins 02-06: function rewritten, tests pass, billing view untouched, at most 3 comment lines, files only read untouched | 5/5 each | 5/5 each | 5/5 each | 5/5 each |
| mention 01, hidden tests: CHF rounds to 0.05 and every caller's result is unchanged (core) | 5/5 | 5/5 | 5/5 | 5/5 |
| mention 02, files that only mention `round_price` untouched (restraint) | 5/5 | 5/5 | 4/5 | 5/5 |
| mention 03-05: at most 3 comment lines, tests pass, no question about callers | 5/5 each | 5/5 each | 5/5 each | 5/5 each |

What this shows:
- **v2 held up on new material.** It scored 100% on both held-out cases on both models.
  Its new rule to fix text the change made false did not spread into edits of descriptive
  mentions: no `with_skill` run edited a file outside `pricing/rounding.py`, added a
  defence or asked about callers.
- **It shows no gain to carry over.**
  - Every arm kept the first login (hidden tests 20/20 across arms).
  - No run copied the last-wins one-liner the user suggested. 18 runs used `setdefault`
    and 2 used a dict comprehension over the reversed events.
  - Every reply in every arm named `billing/trial_clock.sql` (20/20).
  - So the bare model found the reason in the other file without help, as it did in
    every training case.
- **So the held-out result is a core tie with all three competitors**, and within one
  check of each on all checks. With no headroom, it tests only that the skill does no
  harm on new material. It cannot test whether a gain generalises, because there was no
  graded gain to carry over.
- **Ungraded, the skill came out behind the shipped skill on both held-out cases**
  (table above):
  - On first-wins, the shipped skill and the reminder wrote the trial-clock reason into
    the docstring more often (5/5 each against 3/5). The bare model did in 1/5.
  - On the restraint case, every `with_skill` reply reported the search, as did every
    reminder reply. The skill's own Report rule says to mention the sweep only when it
    changed the plan or found something stale. One Haiku reply (run-2) called the four
    descriptive mentions "live" constraints.

## Rulings (overrides) by arm

None. There is no `overrides.json` in any counted iteration, so every grade is the
check's own result. An auditor agent, not a human, made this call. It read every failed
check and every passing result of the heuristic checks in every arm, and re-grading gave
the same numbers.

| Arm | Rulings |
| --- | --- |
| with_skill | 0 |
| shipped_skill | 0 |
| reminder | 0 |
| without_skill | 0 |

The auditor left three close calls unruled, because none was plainly wrong:
- **`iteration-1-haiku`, `dispatched-by-name`, reminder run-1, check 06 (reply).** The
  reply explains only indirectly why `handle_chargeback` stayed. The pass stands.
- **`heldout-sonnet`, `mention-without-constraint`, check 05 (reply).** Two replies end
  with a request about the callers but no question mark:
  - reminder run-2: "Let me know if you want CHF threaded through the invoice, tax, label
    and report code."
  - shipped_skill run-1: "Say if you want that wired in."

  If these count as questions, each of those arms drops to reply 1/2 and a 95.0% mean
  pass rate on `heldout-sonnet`. `with_skill` is unaffected either way.

The auditors found no grader bug in these iterations. The one grader fix (a net count of
added comment lines) came at the gate, before any counted run ([GATE.md](GATE.md)).

## Excluded runs

None, and no run was re-run.
- **Skill reads.** `verify-reads` found a transcript for every skill-arm run in every
  counted iteration: iteration 1, 50 of 50; iteration 2, 25 of 25; held out, 20 of 20.
  Every one read its `SKILL.md` snapshot before its first edit.
- **Held-out arm checks.** The auditor also confirmed that:
  - no held-out skill-arm run read the other skill arm's snapshot;
  - no reminder or bare run read any snapshot.
- **Where the output is.** Each counted iteration stores it as `verify-reads.json`. Its
  `skill_arms` and `skill_arm_runs` entries have the fields that
  `harness.py verify-reads` returned when they were written. No script in the repository
  writes its other lists: other-arm reads, wrong model, and runs with several or no
  transcripts; they come from the out-of-repository wrapper described in
  [incubator/README.md](../../README.md). The `wf_*` transcripts it read are not stored,
  so the reads cannot be re-checked from the repository. `harness.py verify-reads`
  accepted a read of either snapshot when these files were written; since 2026-11-11 it
  requires the arm's own.
- **The one empty diff** is iteration-1 Haiku `without_skill` `sort-relied-on-elsewhere`
  run-2. Its reply deliberately declines to drop the sort and asks the user to choose, so
  it is graded as it stands. It fails check 02.
- **Discovery.** [discovery.py](discovery.py) was not run on any iteration. When each run
  found the evidence is inferred from its reply and diff, not from its transcript.

The gate's 21 bare runs are not counted. They ran on the fixtures before hardening, and
they chose and hardened the cases. No bare gate was re-run on the hardened fixtures, so
iteration 1's `without_skill` arm is the first bare result on them. Its 25/25 core passes
show that the hardening did not create core headroom.

## What with_skill did that the others did not

**Against the shipped skill:**
- **Graded, training only.** `with_skill` kept every live constraint it found: core 25/25
  in each training iteration. The shipped skill broke one it had found in 6 of 25
  iteration-1 runs (core 19/25, p = 0.022), and each reply said so:
  - **The positional break** (Haiku base runs 2 and 3, pointer run-2). The run put
    currency next to amount and left the positional load alone, so currency codes load
    into the wrong column.
  - **The sort break** (Haiku runs 1 and 3, Sonnet run-1). The run dropped the sort and
    rewrote the upload script's comment to say the upload could be rejected. The replies
    cite the request (Haiku run-1: "you asked only to drop it").
- **Held out.** They tie.
- **Ungraded.** `with_skill` kept the form the user named on the positional pair: 10/10
  against 2/10.

**Against the one-line reminder:**
- **Graded.** Nothing reliable. The leads are one or two checks: Haiku 90 against 88 and
  Sonnet 63 against 62 in iteration 1. On held-out Haiku the lead is one check, the
  reminder's `README.md` edit. Core ties everywhere.
- **Ungraded:**
  - **The named form.** `with_skill` kept it on the positional pair 10/10 against 3/10
    (p = 0.003). The reminder sentence has no rule about the requested form. The
    skill's "Keep the form the user named" rule is the likely source; that is an
    interpretation, not tested on its own.
  - **Shorter replies.** In mean words:

    | | Haiku | Sonnet |
    | --- | --- | --- |
    | Training v1 (with_skill against reminder) | 215 against 269 | 196 against 204 |
    | Held out (with_skill against reminder) | 218 against 294 | 162 against 217 |

  - **Smaller diffs.** In mean changed lines, tests included:

    | | Haiku | Sonnet |
    | --- | --- | --- |
    | Training v1 (with_skill against reminder) | 12.1 against 15.8 | 9.3 against 14.0 |

**Against no skill:**
- **Graded.** Nothing reliable. Core ties (25/25 and 10/10 in both arms). The all-checks
  leads are 2 checks in training and none held out.
- **Ungraded:**
  - **The named form** on the positional pair: 10/10 against 0/10.
  - **Fewer documentation edits nobody asked for** on the positional pair: 1/10 against
    4/10 (p = 0.30, not established).
  - **No refusal.** `with_skill` never declined to act. One bare Haiku sort run changed
    nothing and asked the user to choose.
  - **Sort fix kept at the producer:** v2 4/5 against the bare model's 1/5. This
    compares iteration 2 with iteration 1 (p = 0.21).

## What the others did that with_skill did not

- **They fixed the comment the change made false (against v1).** In
  `stale-constraint-elsewhere` every v1 `with_skill` run left that comment in place and
  only reported it. Every run of the other arms corrected it (15/15). Check 05 accepts a
  reply-only report, so the checks did not catch this. v2 fixed it (5/5 corrected).
- **They wrote the reason into the code more often** (held out, first-wins).
  - The shipped skill and the reminder put the trial-clock reason in the docstring in 5/5
    runs each; `with_skill` did in 3/5 (Haiku 1/3).
  - The skill asks for no new comments, which may explain this. That is an
    interpretation, not tested. The shipped skill's aim is to keep that reason beside the
    code.
  - Every arm stayed within the three-line limit.
- **They kept the reply to the change** (held out, restraint case).
  - The shipped skill and the bare model did not report a search when it found nothing.
  - `with_skill` reported one in 5/5 runs, against its own Report rule. So did the
    reminder.
- **Their replies were shorter.** In mean words, `with_skill` replies ran longer than the
  bare model's in every cell, and longer than the shipped skill's in all but held-out
  Sonnet:

  | | with_skill | bare | shipped_skill |
  | --- | --- | --- | --- |
  | Training v1, Haiku | 215 | 192 | 203 |
  | Training v1, Sonnet | 196 | 177 | 175 |
  | Held out, Haiku | 218 | 183 | 186 |
  | Held out, Sonnet | 162 | 148 | 178 |

  v2 replies on training ran 232 (Haiku) and 215 (Sonnet) words. In the iterations where
  all four arms ran, the reminder's replies were the longest in every cell.
- **Sonnet `with_skill` never moved the sort into a consumer.** `with_skill` on Haiku did
  (v1 3/3, v2 1/3). The other arms did too: the reminder in 4/5 runs, the bare model in
  3/5 and the shipped skill in 1/5. The bare count includes Sonnet run-1, whose export
  passes an `ordered=True` flag to an `ORDER BY id` in `fetch_rows`. So this is a
  failure to prevent, not something only the skill did. The v2 Haiku run that moved it
  named `ORDER BY id` as the cheaper option in its reply. It did not use it "because you
  asked for the sort to be dropped". v2's rule says to look for that first.
- **They did not widen the scope.** Only one run in any arm did:
  - It was iteration-1 Sonnet `with_skill`, pointer run-2.
  - It added a currency column to the warehouse table, so an existing warehouse needs a
    manual `ALTER TABLE` before the next load.
  - It passed every check, and the behaviour did not recur in v2.

## Where the numbers come from

- `iterations/<name>/benchmark.json` and `benchmark.md` hold every pass rate, focus
  count, per-case result and per-check result.
- `iterations/<name>/<case>/<arm>/run-K/` holds `grading.json`, `changes.diff` and
  `RESPONSE.md`.
- The writer of this file counted these from each run's files: column placement, where
  the sort went, stale-comment handling, reasons in docstrings, reported searches, reply
  length and changed lines. They are not graded and not in the benchmark.
- Changed lines count the `+` and `-` lines of `changes.diff`, tests included.
