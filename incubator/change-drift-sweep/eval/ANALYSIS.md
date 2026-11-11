# change-drift-sweep: analysis

## Iteration 1

### What ran, and how far it can be trusted

- **Split and arms.** The training split (five cases) ran in all four arms on two models:
  - Haiku: 3 runs per cell, 60 graded runs (`iterations/iteration-1-haiku/`).
  - Sonnet: 2 runs per cell, 40 graded runs (`iterations/iteration-1-sonnet/`).

  Both iterations used the v1 skill. The two snapshots are byte-identical to each other
  and to v1 as committed. `skill/` now holds v2 (`eval/CHANGES.md`).
- **Excluded runs.** Four runs were excluded and re-run, all for an environment fault.
  The run-limits guard misread a `sed -i` heredoc in three Sonnet runs:
  `default-value-drift` shipped_skill run 2, and `unit-spelled-ttl` reminder run 1 and
  with_skill run 1. It misread a `>` inside a heredoc in one Haiku run:
  `pre-existing-drift-reported` shipped_skill run 3. The excluded records are kept in
  `excluded-runs/`.
- **Runs without a reply.** Two graded Haiku runs have no RESPONSE.md: with_skill
  `default-value-drift` run 2 and reminder `unit-spelled-ttl` run 1. The guard blocked a
  Write to a path spelled `/tmp/...`. Neither case grades the reply, so both runs count
  on their repository checks. The reply-length figures below leave them out.
- **One override.** Haiku shipped_skill `default-value-drift` run 3, check 02. The run
  wrote "above 500 rows" for the ledger limit, and the check's limit exclusion knew
  "more than" but not "above".
- **Reads.** Every skill-arm transcript read the snapshot SKILL.md before its first edit:
  53 of them, including the excluded runs. I applied the `verify-reads` rule to the run
  transcripts.
- **Held-out cases.** They had not been run when this analysis and v2 were written, and
  their contents were not opened. One early recursive directory listing printed their
  file and grader file names. Nothing from them informed this analysis or v2.
- **Power.** Two or three runs per cell can detect only large effects. A one-check
  difference between arms is one run doing one thing, and should be read as noise.

Tool-call counts, script calls and token counts below come from the run transcripts.
Each tool call is counted once, by its id, from the assistant messages, and each API
message's output tokens once. Grades come from `grading.json` and `benchmark.md`.

### Results by arm

| Model | Arm | Runs | All checks | Core | Preservation | Restraint | Reply |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Haiku | with_skill | 15 | 96/96 | 60/60 | 30/30 | 3/3 | 3/3 |
| Haiku | shipped_skill | 15 | 95/96 | 60/60 | 30/30 | 3/3 | 2/3 |
| Haiku | reminder | 15 | 96/96 | 60/60 | 30/30 | 3/3 | 3/3 |
| Haiku | without_skill | 15 | 88/96 | 53/60 | 29/30 | 3/3 | 3/3 |
| Sonnet | with_skill | 10 | 64/64 | 40/40 | 20/20 | 2/2 | 2/2 |
| Sonnet | shipped_skill | 10 | 64/64 | 40/40 | 20/20 | 2/2 | 2/2 |
| Sonnet | reminder | 10 | 63/64 | 39/40 | 20/20 | 2/2 | 2/2 |
| Sonnet | without_skill | 10 | 63/64 | 39/40 | 20/20 | 2/2 | 2/2 |

### Headroom: the first bare-model measure of the hardened cases

GATE.md hardened four training cases and did not run the gate again on them, so this is
the first measure of their headroom. "Full core" counts the bare runs that passed every
core check.

| Case | Hardened | Haiku bare, full core | Sonnet bare, full core | Failures in any arm |
| --- | --- | --- | --- | --- |
| `default-value-drift` | no | 3/3 | 1/2 | Sonnet bare run 2 only |
| `unit-spelled-ttl` | yes | 0/3 | 2/2 | Haiku bare 3 runs; Sonnet reminder 1 run |
| `derived-backoff-total` | yes | 3/3 | 2/2 | none |
| `flag-rename-records-stay` | yes | 3/3 | 2/2 | Haiku bare run 1, a preservation check |
| `pre-existing-drift-reported` | yes | 0/3 | 2/2 | Haiku bare 3 runs; Haiku shipped 1 run (reply) |

What the runs show:
- The hardening gave bare Haiku headroom in two cases: `unit-spelled-ttl` and
  `pre-existing-drift-reported`.
- It gave no core headroom in the other two. `derived-backoff-total` is still at ceiling
  for every arm on both models.
- Bare Sonnet passed every hardened case. Its only miss was in the unhardened case. It
  left the same number word in the sync docstring that the gate's Sonnet run left.

### Per case and arm

**`default-value-drift`**
- **Scores.** Every Haiku run in every arm passed 7/7. On Sonnet, with_skill, shipped and
  reminder passed 2/2. Bare run 2 left "fifty at a time" in the sync docstring.
- **with_skill (5 runs).** The same four corrections every time, each restating the new
  figure. No run added a changelog line, and the replies said why: there is no
  `Unreleased` heading.
- **Changelog sections.** Bare runs added an `## Unreleased` section in 5/5 runs,
  shipped in 2/5 and reminder in 0/5. No check grades this.
- **Restating against pointing.** with_skill and reminder restated the figure in every
  corrected line (10/10 runs). The shipped skill named the constant instead in at least
  one line in 4/5 runs, and in 4 runs it added a limit comment beside the constant.

**`unit-spelled-ttl`**
- **Haiku scores.** with_skill, shipped and reminder passed 3/3. Bare failed check 02 in
  3/3 runs:
  - runs 2 and 3 left the wrapped quarter-hour idiom in the forms docstring;
  - run 1 left the views docstring and the banner time, and so also failed check 03.
- **Sonnet scores.** Every arm passed 2/2 except reminder run 2, which left "fifteen
  minutes" in the views docstring.
- **with_skill.** Every run recomputed the banner offset from the new code. Every arm
  kept the three lures that share the figure.
- **The script.** It did not list the wrapped idiom in any Haiku with_skill run (see
  below).

**`derived-backoff-total`**
- **Scores.** Every run of every arm passed every check on both models. The diffs are
  nearly the same across arms, so no arm separates here.
- **Noise in files.** One Haiku with_skill run wrote its arithmetic into the worker
  docstring ("(40 x 31 s = 1,240 s)"). One bare run added a parenthetical. Two Haiku
  shipped runs added a rationale comment above the constant that the request never gave.

**`flag-rename-records-stay`**
- **Core.** Every run of every arm passed every core check.
- **Records.** Haiku bare run 1 added a note line to the accepted ADR, which failed the
  records check.
- **Internal parameter.** Haiku bare run 3 and Sonnet reminder run 2 also renamed the
  internal `since` parameter. No check grades this. No with_skill run did it, and one
  with_skill reply said why it left that parameter alone.
- **Changelog.** with_skill added a line under the existing `Unreleased` heading in 4/5
  runs.
- **Replies.** Every arm called the ADR out of date and mentioned superseding it. One
  with_skill reply suggested superseding while saying the rename does not contradict the
  ADR.

**`pre-existing-drift-reported`**
- **Haiku scores.** with_skill and reminder passed 3/3. Shipped run 2's reply never
  mentioned the flush mismatch. Bare failed check 02 in 3/3 runs: each left the
  throughput figure in the sender docstring, and run 3 also left the burst cost.
- **Sonnet scores.** Every arm passed 2/2.
- **The flush sentence.** No run in any arm corrected it. Every run left it, and every
  run but one reported it (Haiku shipped run 2).
- **Word form.** Haiku with_skill wrote the new size as words in 3/3 runs, keeping the
  sentence's form, and reminder did so in 2/3. Shipped and bare used digits.

### Does with_skill beat the other arms?

What the runs show:
- **Haiku, core.** with_skill 60/60, shipped 60/60, reminder 60/60, bare 53/60.
- **Haiku, all checks.** with_skill 96/96 and reminder 96/96, shipped 95/96 (one reply
  check), bare 88/96.
- **Sonnet, core.** with_skill 40/40 and shipped 40/40, reminder 39/40, bare 39/40.
- **Sonnet, all checks.** with_skill 64/64 and shipped 64/64, reminder and bare 63/64.
- **Margins.** with_skill never failed a check. Against bare Haiku its margin is 8
  checks: 7 core and 1 preservation, over 15 runs and 3 of the 5 cases. Against reminder
  and shipped its margin is 0 or 1 check on each model, which is a single run.

Interpretation:
- On Haiku, the one-sentence reminder and the shipped skill account for the whole gain
  over the bare model.
- On Sonnet, these cases separate no arms.
- Iteration 1 does not show that the skill adds anything over the reminder or the
  shipped skill. That is the tie the README expected on core checks.

### value_drift.py

What the runs show:
- **Who ran it.**
  - Haiku with_skill: 15 of 15 runs, with 1 to 4 calls each. A run usually called it
    once before or at its first edit, and again as a check after editing.
  - Sonnet with_skill: 0 of 10 runs. Every Sonnet run printed every file, with `cat` in
    a loop or a grep followed by `cat`, and edited with `sed`.
  - No other arm ran it.
- **Flags.** `--strings` in 11/15 runs, `--near` in 4, `--new` in 2 and `--unit` in 2.
  One `--unit` was a usage error (`--unit rows`), and the run retried without it.
- **Derived figures.** In 8 of the 12 runs on the four numeric cases, the first call
  passed at least one figure worked out from the old value, as step 1 asks.
- **No flood.** The first call listed 3 to 12 prose lines in 3 to 9 files. The lines
  that were not living descriptions fall into three kinds:
  - records, correctly marked `record?`;
  - lures that share the number;
  - one Markdown step number ("3.").

  The runs left all of them alone.
- **Never the only route to a fix.** Every Haiku run printed every file that held a
  graded statement before its first script call or in the same command, or it ran the
  script only after editing. The script served as a checklist and a final check.
- **Miss 1: wrapped forms.** In `unit-spelled-ttl` the script left out the docstring
  sentence whose quarter-hour idiom wraps across a line break, in 3 of 3 runs. Two runs
  passed that very phrase as `--old`. The third passed the old value in seconds, whose
  conversions include the idiom. The script matched one line at a time. All three runs
  fixed the sentence because they had read the file.
- **Miss 2: the scope of `--near`.** In `unit-spelled-ttl` run 1, the run put a value
  under 10 in the same call as the old timeout and the banner offset. It then added
  `--near "session|idle"`, as SKILL.md says to do for small values. The filter applied to
  every value in the call and dropped the banner line, a derived figure on a line that
  names neither word. The same call's `--unit min` read the old value, given in seconds,
  as 900 minutes. The run recovered by reading.

Interpretation:
- Both models read every file of these 9- to 13-file repositories, so the script has no
  room to show value here.
- Its recall matters only where a run cannot read everything, and there the wrap miss
  would have become a real miss.
- Sonnet shows that a run skips the script when reading is cheaper.

### Harm

What the runs show:
- **Preservation and restraint.** with_skill failed none of these checks: 33/33 on
  Haiku, 22/22 on Sonnet. It edited no record, ADR, outside fact or shared-number lure.
- **Restraint beyond the checks.** with_skill made none of the extra changes that other
  arms made in some runs (all described above):
  - it added no changelog section where none existed;
  - it renamed no internal parameter;
  - it added no unrequested rationale comment.
- **Noise in files.** One with_skill run wrote its arithmetic into a docstring.
- **Longer replies.** with_skill replies were the longest on both models.

  | Model | with_skill | shipped_skill | reminder | without_skill |
  | --- | --- | --- | --- | --- |
  | Haiku, mean (median) words | 228 (232) | 197 (203) | 208 (199) | 186 (174) |
  | Sonnet, mean (median) words | 245 (247) | 219 (218) | 199 (214) | 169 (186) |

  One cause is a sentence that reports an empty category ("none found", "no changelog,
  ADR or instruction file ..."). A keyword count, so the figures are approximate:
  - with_skill: 5/14 replies on Haiku, 10/10 on Sonnet;
  - reminder: 10/14 and 6/10;
  - shipped: 0/15 and 2/10;
  - bare: 1/15 and 0/10.

  One Haiku with_skill reply quoted the script command.
- **Cost.** Means per graded run:

  | Model | Measure | with_skill | shipped_skill | reminder | without_skill |
  | --- | --- | --- | --- | --- | --- |
  | Haiku | tool calls | 19.7 | 14.9 | 15.4 | 17.1 |
  | Haiku | output tokens | 7.7k | 6.0k | 6.1k | 5.3k |
  | Sonnet | tool calls | 7.5 | 7.5 | 5.6 | 4.8 |
  | Sonnet | output tokens | 2.9k | 2.8k | 2.3k | 2.0k |

  Haiku runs made 0 to 20 Edit calls each. In every Haiku arm, 26% to 41% of the Edit
  calls failed with "File has not been read yet", so retries inflate the Haiku counts
  across the board.

Interpretation:
- The skill's harm here is length and cost.
- The extra length comes partly from answering the reply list item by item, empty items
  included.
- The harm is real but mild, and the reminder arm shows the same empty-category habit.

### Revision decision (v2)

No graded failure calls for a revision. Two misses in the search step trace to the skill
package, and a general rule fixes each. v2 makes both changes, in one revision.
`eval/CHANGES.md` records the details.

1. **Script.** It reads each prose line together with the next line of the same
   comment, docstring or paragraph. A form wrapped across the break is found and listed
   where it starts. A number at a line end is judged by the unit on the next line.
   - On the training fixtures, the missed sentence is now listed.
   - With the runs' own arguments, the output on the other four fixtures is unchanged.
2. **SKILL.md.** A value under 10 is searched in a call of its own, because `--near`
   and `--unit` apply to every `--old` in a call.

Not changed in v2:
- **Reply length.** It is a candidate for v3, a rule to leave out empty items, if
  iteration 2 shows it again.
- **Restating the value against naming the constant.** Both pass, and SKILL.md already
  allows either.

What iteration 2 can and cannot show:
- with_skill is already at ceiling on the training split, so v2 cannot raise a graded
  result there.
- Iteration 2 can check only that v2 does no harm, and that the script now lists wrapped
  forms.
- To measure the search step, and so the script, the cases would need repositories too
  large for a run to print whole.

## Iteration 2

### What ran, and how far it can be trusted

- **Split and arm.** The training split ran again, in the `with_skill` arm only, on v2:
  - Haiku: 3 runs per case, 15 runs (`iterations/iteration-2-haiku/`).
  - Sonnet: 2 runs per case, 10 runs (`iterations/iteration-2-sonnet/`).

  Both snapshots are byte-identical to the current `skill/`.
- **Comparison across runs.** No other arm ran. v2 is compared with the iteration-1
  runs of v1 and of the other arms. The other arms do not read this skill, so v2 cannot
  change what they do. But they are separate samples from a separate run.
- **Reads.** `verify-reads` found 15/15 and 10/10 runs that read the snapshot SKILL.md
  before any edit. In every transcript the read was the second tool call, right after
  `prompt.txt`. Several Sonnet runs edited only through Bash, always after the read.
- **No exclusions, and every run wrote a reply.**
- **Two rulings, both on the reply check of `pre-existing-drift-reported`:** Haiku run 3
  and Sonnet run 1.
  - Each reply had one paragraph that gave the doc's 60 seconds and the code's
    `FLUSH_INTERVAL_S = 30`. The paragraphs said "This was already false" and "Drift
    that was already there".
  - The check failed both only for a missing contrast word. Its list has "wrong",
    "stale", "incorrect" and "outdated", but not "false" or "drift".
  - Before the rulings, v2 scored 95/96 on Haiku and 63/64 on Sonnet.
- **Audit coverage.** The auditor read every changed line and every heuristic result in
  all 25 runs, and found no false pass.

### Results

| Model | v1, iteration 1 | v2, iteration 2 | v2 before rulings | Best other arm, iteration 1 |
| --- | --- | --- | --- | --- |
| Haiku | 96/96, core 60/60 | 96/96, core 60/60 | 95/96 | reminder 96/96 |
| Sonnet | 64/64, core 40/40 | 64/64, core 40/40 | 63/64 | shipped_skill 64/64 |

Every v2 run passed every check in every case, as v1 did. As expected, v2 could not
raise a graded result.

### Did each change hit its target?

**1. The script reads a line with the next line of its block.**

What the runs show:
- In `unit-spelled-ttl`, Haiku runs 1 and 3 ran the script before editing. Both lists
  included the wrapped quarter-hour idiom in the `auth/forms.py` docstring.
- Their first call listed 10 prose lines in 7 files, against 9 in 6 for v1 runs with
  similar arguments.
- Run 2 ran the script only after its edits.
- After editing, run 3's list marked the wrapped "half an hour" `states new`.

Interpretation: the fix works on the miss it was made for. No fix depended on it, since
each run had printed the files first.

**2. A value under 10 gets a call of its own.**

What the runs show:
- Haiku used `--near` in 4 of 15 runs and Sonnet in 2 of 10.
- In `derived-backoff-total`, Haiku runs 1 and 3 each still put `--near` on a call that
  also held the derived figures, the case the new sentence warns about.
- Run 3 had first searched the 4 in a call of its own, as v2 asks.

Interpretation: the sentence was followed once and its warning missed twice. Every run
read every file and passed every check, so a dropped hit cost nothing here. The change
is untested.

### Other differences from v1 (ungraded)

- **Pre-existing drift corrected on Sonnet.** Both Sonnet runs changed the flush
  sentence to 30 seconds, toward the code. Run 2 also changed "a minute" to "half a
  minute". Check 03 accepted both. No run of any arm made this correction in iteration
  1. Haiku v2 left the sentence and reported it, as v1 did. SKILL.md allows both.
- **Sonnet ran the script in 2 of 10 runs**, both in `default-value-drift`, with
  `--near` and `--strings`. v1 Sonnet never ran it. Haiku ran it in 15 of 15, as before.
- **One Haiku run renamed the internal `since` parameter** (`flag-rename-records-stay`
  run 1). No v1 skill run did. One bare and one reminder run did in iteration 1.
- **Pointing to the constant.** In `default-value-drift`, Haiku run 3 wrote "asks for
  PAGE_SIZE rows per request" and "a page at a time". Every v1 skill run had restated
  the figure.
- **No arithmetic went into the `derived-backoff-total` docstrings.** One v1 run had
  written it there.
- **Changelog.** v2 added a line under the existing `Unreleased` heading in 5/5
  `flag-rename-records-stay` runs (v1: 4/5). As in v1, it added none in
  `default-value-drift`.
- **Word form.** Haiku again wrote "two hundred and fifty at a time" in 3/3 runs.
  Sonnet used digits.

### The reply check and the skill's own words

SKILL.md says "A sentence already false before your change is not your drift". Its
reply list asks for "Drift your change did not cause". Two of five v2 replies used those
words in place of a listed contrast word. In v1, no skill reply needed a ruling.

Interpretation: on any cross-arm iteration with v2, the reply check would lean against
the skill arm, unless "false" and "drift" join `_C5_CONTRAST` or each miss gets a
ruling.

### Harm and cost

- **Files.** No preservation or restraint failure: 33/33 on Haiku and 22/22 on Sonnet.
- **Replies did not get shorter.** v2 left the reply rules alone. Haiku replies averaged
  245 words, median 257 (v1: 228 and 232). Sonnet averaged 234, median 222 (v1: 245 and
  246).
- **Cost:**
  - Haiku: 17.9 tool calls and 7.5k output tokens per run (v1: 19.7 and 7.7k).
  - Sonnet: 8.1 tool calls and 3.0k output tokens (v1: 7.5 and 2.9k).

### Interpretation

- v2 did no harm. It fixed the script miss it targeted and left the `--near` change
  untested.
- No v3 was made. Replies were again the longest, but no graded failure called for a
  change. The held-out run came next.

## Held-out cases

### What ran, and how far it can be trusted

- **Split and arms.** Both held-out cases, in all four arms, on v2:
  - Haiku: 3 runs per cell, 24 runs (`iterations/heldout-haiku/`).
  - Sonnet: 2 runs per cell, 16 runs (`iterations/heldout-sonnet/`).

  They ran once, after the last skill edit. The v2 and shipped-skill snapshots are
  byte-identical to the current files.
- **Reads.** `verify-reads` found 12/12 Haiku and 8/8 Sonnet skill-arm runs that read
  their snapshot before any edit, as the second tool call. No reminder or bare run read
  a SKILL.md.
- **No exclusions and no rulings, and every run replied.** Neither case grades the reply.
- **Audit coverage.** The auditor read every diff and every heuristic result in all 40
  runs, and upheld all four failures.
- **Exposure.** No skill edit drew on these cases.
  - `pointer-comment-needs-nothing` was described in CASES.md when the skill was first
    written, so it is a restraint guard, not a clean test.
  - `poll-interval-average-wait` was never described anywhere a skill writer reads.
  - The v2 writer's directory listing printed both cases' file names.

### Results by arm

| Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| Haiku (6 runs per arm) | 36/36, core 18/18 | 35/36, core 17/18 | 36/36, core 18/18 | 34/36, core 16/18 |
| Sonnet (4 runs per arm) | 24/24, core 12/12 | 24/24, core 12/12 | 24/24, core 12/12 | 23/24, core 11/12 |

Preservation and restraint were full in every arm. Every failure is check 02 of
`poll-interval-average-wait`.

### `poll-interval-average-wait`: the generalisation check

The case tests two things SKILL.md does not name:
- a figure derived by halving the old value, an average wait, stated twice: in
  `docs/fulfilment.md`, and in an `orders/queue.py` docstring that never names
  `POLL_INTERVAL_S`;
- a dated record that sits as a section of a living page.

What the runs show:
- **with_skill: 5/5 runs corrected both averages.**
  - The 3 Haiku runs each worked out the halved figure themselves (150 s, 2.5 min, "two
    and a half minutes") and passed it to the script in their first call.
  - The script listed "about 150 s" in all three runs. It listed "two and a half
    minutes" only in the run that passed that phrase as literal text, the gap
    HELD-OUT.md predicted.
  - Each Haiku run had printed every file before its first script call.
  - The 2 Sonnet runs did not run the script. Run 1 printed every file. Run 2 grepped
    for the old forms, 150 among them, and opened the files they named.
- **reminder: 5/5**, with the same five edits as the skill.
- **shipped_skill: 5/5 corrected both averages.** Haiku run 3 failed check 02 on a gloss:
  "half a poll interval (ten minutes) later on average". The check reads the bracket as
  600 s in a sentence about the average. The bracket may instead gloss "a poll
  interval", and no reply settles it, so no ruling was made.
- **shipped_skill comments.** It added a comment above `POLL_INTERVAL_S` in 5/5 runs,
  and 4 of them restate "Ten minutes".
- **without_skill:** Haiku run 2 and Sonnet run 1 left "about 150 s" in the queue
  docstring. Haiku run 1 wrote the same gloss as the shipped run.
- **The record inside a living page held in every arm.** No run in any arm changed the
  dated "Past incidents" entry. The same held for the storefront's cache and quota and
  for the packers' five minutes (20/20 on check 04).

Interpretation:
- The skill generalised to a form it does not list. Its derived-figure step led every
  Haiku run to compute the halved figure before searching, and every run then corrected
  it.
- The script's own matching did not generalise. Reading found the worded average.
- The reminder sentence, which names "figures computed from it", did as well in every
  run. So did the shipped skill on the figures themselves.

### `pointer-comment-needs-nothing`: the restraint guard

What the runs show:
- All 20 runs passed every check.
- Every with_skill, shipped and reminder run changed only `MAX_PARALLEL = 8`.
- The skill runs' script lists for `--old 4` held only lines to leave:
  - the "tried four times" retry count;
  - the four-second dashboard refresh;
  - the pointer comments, in runs that also passed `MAX_PARALLEL`;
  - a CHANGELOG entry and a dated report, both marked `record?`.

  Every skill run left them all.
- 4 of 5 bare runs added a new `## Unreleased` CHANGELOG section, which the graders
  allow.

Interpretation: the skill did not make agents over-edit, which is the risk this case
exists to catch.

### Does with_skill beat the other arms on the held-out cases?

What the runs show:
- **Haiku.** with_skill 36/36 and reminder 36/36. The shipped skill scored 35/36 (the
  gloss), and bare 34/36.
- **Sonnet.** with_skill, shipped and reminder all scored 24/24, and bare 23/24.
- **Against the bare model.** In `poll-interval-average-wait`, with_skill had full marks
  in 5/5 runs and the bare model in 2/5 (two-sided Fisher p = 0.17).

Interpretation: the held-out pair repeats the training result. It is a tie with the
reminder and the shipped skill, and a small, noisy lead over the bare model.

### Harm and cost

- **Files.** No preservation or restraint failure in any arm. The skill added no
  changelog section and no comment beside the constant.
- **Replies were the longest again.** Mean words, with medians in brackets:

  | Model | with_skill | shipped_skill | reminder | without_skill |
  | --- | --- | --- | --- | --- |
  | Haiku | 222 (230) | 180 (192) | 201 (196) | 136 (126) |
  | Sonnet | 212 (204) | 157 (150) | 178 (179) | 169 (168) |

- **Cost.** Means per run:

  | Model | Measure | with_skill | shipped_skill | reminder | without_skill |
  | --- | --- | --- | --- | --- | --- |
  | Haiku | tool calls | 15.3 | 12.2 | 14.5 | 12.7 |
  | Haiku | output tokens | 5.9k | 4.9k | 5.2k | 3.7k |
  | Sonnet | tool calls | 5.8 | 5.0 | 3.5 | 7.5 |
  | Sonnet | output tokens | 2.1k | 1.9k | 1.5k | 2.4k |

### Across all 165 runs

- With the skill, every run passed every check. The reminder and the shipped skill tied
  it within one run on each model, in training and held out.
- The README set a test in advance: if the shipped arm tied on the rename case or on
  every case, the skill is a plugin enhancement (#21, #48), not a new skill. The shipped
  arm tied on the rename case and came within one run on every other case.
- The parts that set the skill apart, the script and the record sort, made no difference
  here. Every run could read every file, and every arm kept the records the checks
  protect.
- To measure what the skill adds, a case has to need the search step. It would have to
  be too large to read whole, and gated so that the reminder also misses.
