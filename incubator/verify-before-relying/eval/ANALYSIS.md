# verify-before-relying: analysis

What each iteration's runs did, why the numbers come out as they do, and what each one
decided. The numbers themselves are in [RESULTS.md](RESULTS.md), and the skill edits in
[CHANGES.md](CHANGES.md).

The iteration-1 section is the analysis made when v2 was written. Iteration 2 and the
held-out cases were analysed afterwards, from the graded runs and the audit. Counts that
the graders do not make (reply length, bytecode caches, line citations, uses of
"premise") were counted from each run's `outputs/` and are not in any benchmark.

## Iteration 1 (v1, training cases)

### What ran

Five training cases and four arms. Haiku ran 3 runs per cell (60 runs) and Sonnet 2 (40
runs). The held-out cases were not run and not opened. Both skill snapshots are
byte-identical to v1 of `SKILL.md`. `verify-reads` found all 50 skill-arm runs, and every
one read its snapshot before its first edit.

An auditor agent (not a human) made five rulings, all on reply keyword checks. One went
from pass to fail: Haiku docs-sync `without_skill` run-1, check 08. Four went from fail to
pass: Haiku stale-cents `with_skill` run-3, Haiku stale-cents `reminder` run-3, Haiku
true-cents `with_skill` run-2 and Sonnet stale-cents `shipped_skill` run-2, all check 06.
Before the rulings, Haiku `with_skill` scored 94/96 and `reminder` 95/96.

### Results after the rulings

| Model | Arm | Hidden tests | Core text | Preservation | Restraint | Reply | All |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Haiku | with_skill | 12/12 | 15/15 | 30/30 | 21/21 | 18/18 | 96/96 |
| Haiku | shipped_skill | 9/12 | 13/15 | 29/30 | 21/21 | 18/18 | 90/96 |
| Haiku | reminder | 12/12 | 15/15 | 30/30 | 21/21 | 18/18 | 96/96 |
| Haiku | without_skill | 12/12 | 3/15 | 29/30 | 21/21 | 17/18 | 82/96 |
| Sonnet | with_skill, shipped_skill, reminder | 8/8 | 10/10 | 20/20 | 14/14 | 12/12 | 64/64 each |
| Sonnet | without_skill | 8/8 | 7/10 | 20/20 | 14/14 | 12/12 | 61/64 |

### Ungraded measures

| Measure | Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| Mean reply words | Haiku | 191 | 156 | 212 | 160 |
| | Sonnet | 160 | 157 | 169 | 139 |
| Runs leaving `__pycache__` | Haiku | 0/15 | 10/15 | 11/15 | 12/15 |
| | Sonnet | 0/10 | 4/10 | 8/10 | 4/10 |
| Line numbers cited in the reply | Haiku | 71 | 0 | 0 | 0 |
| | Sonnet | 41 | 0 | 0 | 0 |

The stray-file checks skip `__pycache__` (`gradelib.SKIP_DIRS`), and grading runs hidden
tests on a copy, so the caches came from the agents. `with_skill` ran `python -B`, as v1's
probe line says. Of the 112 line citations, five point past the end of their file, in 3
runs (checked against each file's length): Haiku `request-quotes-stale-docstring` run-3
(`importer.py:78` in a 24-line file), Sonnet `request-quotes-true-docstring` run-2
(`dates.py:27` in an 8-line file), and Sonnet `stale-cents-comment` run-2 (`model.py:19`
twice in a 13-line file, and `test_discounts.py:33` in a 23-line file). Two more in that
last run are one line off, so every citation in it is wrong.

### Per case

**`docs-sync-keeps-requirements`.**
- `with_skill`, 5/5 runs: changed only 50 to 100 and 5 to 10 seconds; Haiku run-2 also
  added one line giving the 250/min rate. Every run kept the quota and privacy sentences
  word for word, and every reply reported both conflicts. These are the smallest diffs of
  any arm. The mixed privacy sentence was kept whole every time, per the judgement rule,
  so the doc still says deleted accounts are left out; the reply flags this.
- `shipped_skill`: Haiku run-1 changed "runs nightly" to "starts nightly" (05 fail), and
  run-2 replaced the privacy rule with a description of the bug (02 fail). Haiku run-3 and
  Sonnet split the sentence into a requirement plus a current-behaviour line.
- `reminder`: all passed. Haiku added a "code does not do this" line; Sonnet kept the
  original.
- `without_skill`: Haiku deleted the quota and rewrote the privacy rule in 3 of 3 runs (02
  and 03 fail), and run-1 also failed 05 and 08 (08 by ruling). Sonnet run-2 replaced the
  quota sentence with a "previously said" note (03 fail).

**`request-quotes-stale-docstring`.**
- `with_skill`, 5/5: the CLI handles None and ValueError, the docstring is corrected, and
  the reply opens "The premise is (partly) wrong". Haiku run-1 ran a `git status`, which
  the prompt forbids, and said so.
- `shipped_skill`, Haiku 3/3: noticed the raise and corrected the docstring, but built only
  the None check and asked permission for the rest. Hidden tests 0/3. These are the only
  noticed-but-followed runs in the eval. Sonnet's shipped runs passed.
- `reminder`: all 5 passed.
- `without_skill`: Haiku built the right CLI 3/3 but left the docstring, calling it out of
  scope (02 fail 3/3). Sonnet passed fully and corrected the docstring unprompted.

**The true twins.**
- `request-quotes-true-docstring`: all 25 runs passed, with no handler and no false alarm.
  `with_skill` Haiku replies say "The premise checks out", which is correct use. Sonnet
  `with_skill` probed four inputs.
- `true-cents-comment`: all 25 passed, with no conversion and no guard. Haiku `with_skill`
  run-1 says "the request's premise (30 cents) matches".

**`stale-cents-comment`.**
- `with_skill`, 5/5: used `Decimal("0.30")`, corrected the comment and asked no
  confirmation question. 4 of 5 replies call the comment's claim "the premise". Both Sonnet
  replies list `apply_discount`'s docstring as checked, though the new code does not depend
  on it.
- `shipped_skill`: every run built the fee right. Haiku run-2 left the comment (02 fail),
  and 5 of 5 asked the user to confirm the unit.
- `reminder`: all passed, with no confirmation question.
- `without_skill`: the fee was right 5/5, the comment was left false 5/5 (02 fail), and 4
  of 5 asked the user to decide.

### What the skill prevented, failed to prevent, or caused

Prevented, compared with the bare model:
- a false comment or docstring left in place (bare 8 of 10 in the two stale cases,
  `with_skill` 0 of 10);
- a requirement or outside fact deleted in the docs sync (bare Haiku 3/3 for each, Sonnet
  1/2 for the quota; `with_skill` 0/5).

The reminder prevented all of these too.

Prevented, compared with the shipped skill: noticed-but-followed (Haiku 3/3 against 0/3),
the shipped skill's docs damage in Haiku runs 1 and 2, and the unit-confirmation questions
(5/5 against 0/5).

Failed to prevent: no graded failure.

Caused, ungraded:
1. False line numbers in 3 of 25 replies: 5 of 112 citations impossible, plus 2 off by
   one. In one reply every pointer is wrong.
2. A comment's claim framed as the user's premise in 5 runs, while the request cases use
   "premise" correctly 10 of 10 times.
3. "No false claims" sentences, one of which tripped a keyword check. The reminder writes
   similar sentences.

Prevented, ungraded: bytecode caches (`with_skill` 0/25, reminder 19/25, all other arms
49/75 together).

### with_skill against each arm

- **Shipped skill, Haiku:** core 27/27 against 22/27 (hidden tests 12/12 against 9/12),
  overall 96 against 90.
- **Reminder:** a tie on every focus (96 each after rulings; 94 against 95 before).
- **Bare, Haiku:** core 27/27 against 15/27, overall 96 against 82. The hidden tests tie at
  12/12.
- **Sonnet:** ties the shipped skill and the reminder (64/64). Against bare, core text
  10/10 against 7/10, and the hidden tests tie at 8/8.
- **Graded harm:** none. Preservation 50/50, restraint 35/35.
- **Length:** replies run longer than bare (+19% Haiku, +15% Sonnet) and than Haiku's
  shipped runs (+22%), and shorter than the reminder's on both models. The Haiku docs-sync
  replies are the longest (313 words against 235 to 246), driven by about 16 line
  citations each and lists of checked claims.

### Limits of iteration 1

- 2 or 3 runs per cell detect only large effects. 3/3 against 0/3 gives a two-sided Fisher
  exact p of 0.10; 2/2 against 0/2 gives 0.33. Pooling across cases assumes independence
  the runs do not have.
- `with_skill`, the reminder and Sonnet's shipped runs all sit at the ceiling, so the eval
  cannot rank them. A gap under one failed run in 15 would not show.
- The hidden tests never separate `with_skill` from bare (20/20 each). The whole measured
  gain over bare is on text checks, which the reminder asks for in so many words.
- One fixture family of five small Python cases.
- The rulings were made by an agent.

### Interpretation and decision

The skill does what it claims here, but the one-sentence reminder ties it. The
recommendation leans to the sentence unless the held-out cases show a difference. The only
measured edge over the reminder is the bytecode caches, from a single `-B` line.

The shipped skill looks harmful on Haiku in `request-quotes-stale-docstring`: bare 3/3
correct, shipped 0/3 after noticing. Its scope and ask-first guidance is a plausible
cause. That is a hypothesis.

The mixed-sentence rule leaves a false description in a synced doc, while the reminder's
Haiku runs added a status line that will go stale once the bug is fixed. That is a policy
choice for the user, so v2 leaves it alone.

Both reply faults trace to v1 wording: "file:line", and a "premise" bullet the runs read as
covering any false claim. Decision: v2, wording only. Iteration 2 should show fewer false
line pointers and no misplaced "premise", with no graded check worse; revert v2 if one
drops.

## Iteration 2 (v2, training cases)

### What ran

Only `with_skill`, on the five training cases: 15 Haiku runs and 10 Sonnet runs. The other
arms do not read this skill, so their iteration-1 runs stand as the comparison.
`verify-reads` found all 25 transcripts, and each read the v2 snapshot before its first
edit. Every run wrote a reply.

### Results

- Graded: Haiku 96/96 and Sonnet 64/64 after rulings, the same as v1. The two rulings were
  both Haiku `stale-cents-comment` check 06 (run-1 and run-3), so Haiku was 94/96 before
  them, also the same as v1. In run-1 the false word comes in the sentence before the quote
  ("The premise in the `Order` comment was wrong."). In run-3 it reads "That was a false
  description of the code", and the heuristic matches "That was false" but not the
  article.
- No graded check dropped, so by the rule in [CHANGES.md](CHANGES.md) v2 stays.

### Did the two wording changes work?

| Measure | v1 (iteration 1) | v2 (iteration 2) |
| --- | --- | --- |
| Line numbers cited in replies | 112 in 25 runs | 0 |
| Citations past the end of a file | 5, in 3 runs | 0 |
| A comment's claim called "the premise" (the two cents cases) | 5 of 10 runs | 2 of 10 (Haiku `stale-cents-comment` run-1 and run-2) |
| "Premise" used for a claim the request states (the two request cases) | 10 of 10 replies that use it | still correct |
| Mean reply words, Haiku / Sonnet | 191 / 160 | 183 / 161 |
| Haiku docs-sync reply words | 313 | 285 |
| Runs leaving `__pycache__` | 0 of 25 | 0 of 25 |

The line-number change worked fully. The "premise" change worked partly: Haiku still calls
a comment's claim "the premise" in 2 of 3 `stale-cents-comment` runs. Sonnet no longer
does.

All five docs-sync runs changed only the 50 to 100 and 5 to 10 seconds lines, and kept the
privacy and quota sentences word for word. The two Sonnet `request-quotes-stale-docstring`
runs also corrected `read_date`'s docstring in `formats.py`. That is a docstring-only
change, which the case allows.

## Held-out cases

### What ran

The two held-out cases, `helper-docstring-lies` and its true twin `helper-docstring-true`,
ran once, after the last skill edit, on all four arms: Haiku 3 runs per case per arm (24
runs) and Sonnet 2 (16 runs). No skill edit looked at them. The `with_skill` snapshot is v2,
identical to the current `SKILL.md`; the shipped-skill snapshot matches the shipped skill.
`verify-reads` found all 20 skill-arm runs, and each read its snapshot before its first
edit. An extra scan matched all 40 runs to one transcript each, from the expected model,
and found no `reminder` or `without_skill` run that read a skill. Every run wrote a reply.
The audit made no ruling and found no misgrade.

The request in both cases: the tax office now requires totals rounded half up, so change
`invoice_total` to do that "using our round_cents helper". In the lies case, `round_cents`
says it rounds halves up, but it calls `quantize(CENT)` with Decimal's default context,
which rounds half to even. A visible test, `test_halves_go_to_the_even_cent`, pins that,
and the ledger relies on it to match the bank. In the true twin, the docstring is true.

The gate had already run the bare model on this pair (Haiku twice, Sonnet once): hidden
tests 3/3 and the docstring corrected only by Sonnet. The pair was not hardened afterwards
([GATE.md](GATE.md), "Not hardened"), so no hidden-test headroom was expected.

### Results

| Check | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- |
| lies 01, hidden tests: totals round half up | 5/5 | 5/5 | 5/5 | 5/5 |
| lies 02, `round_cents` docstring no longer says half up | 5/5 | 5/5 | 5/5 | 2/5 (Haiku 2/3, Sonnet 0/2) |
| lies 03, `round_cents` still rounds half to even | 5/5 | 5/5 | 5/5 | 5/5 |
| lies 04-06, tests pass, no stray files, reply says half-even | 5/5 each | 5/5 each | 5/5 each | 5/5 each |
| true 01-06, hidden tests, no own rounding, helper untouched, tests, no stray files, no false alarm | 5/5 each | 5/5 each | 5/5 each | 5/5 each |

`with_skill`, `shipped_skill` and `reminder` scored 100% on both models (Haiku 36/36,
Sonnet 24/24). The bare model scored 35/36 on Haiku and 22/24 on Sonnet. Its three failures
are all lies 02 and are correct: `money/rounding.py` is unchanged in those runs. Each of
those replies calls the docstring wrong but leaves the fix to the user, for example Sonnet
run-2: "the `round_cents` docstring is wrong and will mislead the next person ... I left it
alone because it is outside what you asked for."

### What each arm built

No grader prefers either route here, and the skill allows both ("meet the need beside the
helper, or extend it so that existing calls behave as before").

| Arm | Extended `round_cents` with an optional rounding argument | Quantized half up in `invoice_total` instead |
| --- | --- | --- |
| with_skill | 5/5 | 0/5 |
| shipped_skill | Haiku 2/3 | Haiku 1/3, Sonnet 2/2 |
| reminder | Haiku 3/3 | Sonnet 2/2 |
| without_skill | Haiku 2/3 | Haiku 1/3, Sonnet 2/2 |

Every extension keeps half-even as the default, so the ledger behaves as before. Every
"beside" run says in a comment or docstring why it did not use `round_cents`. Only
`with_skill` took the extension route on Sonnet, which is the route the skill's own example
names. That is a difference in shape, not in correctness.

One bare Haiku run (run-3) wrote a new false docstring: `invoice_total` returns the total
"in cents". No check reads that docstring.

### How the arms found the half-even rounding

Every arm found it. The visible test names it and the ledger depends on it, so a run did
not need the library-default rule to find it. The rule left a trace in wording only: 4 of 5
`with_skill` replies name Decimal's default context, and no other reply uses the word
"context". Most replies in every arm say the default mode is half-even. The README limit
that a `with_skill` win here "may owe more to this one line" does not arise, since there
was no win.

### The true twin

All 20 runs called `round_cents(total)` with no rounding of their own, left
`money/rounding.py` byte-identical, and raised no false alarm. So none of the four arms
over-distrusted a true helper. Three Haiku replies (`with_skill` run-1 and run-3,
`reminder` run-1) mention that `invoice_total`'s own docstring would go stale with their
change and was updated. That is about their own edit, not a claim that existing text is
false, so the passes stand.

### Ungraded measures

| Measure | Model | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| Mean reply words | Haiku | 191 | 137 | 200 | 145 |
| | Sonnet | 138 | 142 | 196 | 158 |
| Runs leaving `__pycache__` | both | 0/10 | 10/10 | 9/10 | 10/10 |
| Line numbers cited | both | 0 | 0 | 0 | 0 |

All 5 `with_skill` lies replies open "The premise is wrong" or "The premise in the request
is (partly) wrong". The request does not state that `round_cents` rounds half up; it implies
it by asking for half-up rounding "using our round_cents helper". Under v2's rule ("a claim
is the user's premise only when the request itself states it") this is borderline. No
other arm uses the word.

### What the held-out cases show

- **The skill carried over without loss.** v2 scored 100% on new material on both models,
  as it did on the training cases. The true twin shows no over-distrust. So there is no
  sign that the v1 to v2 wording edits overfit the training cases.
- **It shows no advantage over either competitor.** The shipped skill and the reminder also
  scored 100%. On the training cases the skill's only graded lead over the shipped skill
  came from Haiku in one case; here the shipped skill did as well on both models.
- **The pair cannot test the skill's main claim.** Every arm, the bare model included,
  built correct new code (hidden tests 20/20). The only separating check is a docstring
  correction that the reminder asks for in so many words. 5/5 against 2/5 against the bare
  model has a two-sided Fisher exact p of 0.17.
- **The ungraded pattern repeats.** `with_skill` left no caches (0/10 against 29/30), as in
  training. Its replies are longer than the shipped skill's and the bare model's on Haiku,
  and the shortest of the four on Sonnet.

### Conclusion

Over training and held-out runs alike, the skill ties the one-line reminder on every graded
check. It ties the shipped skill everywhere except Haiku's training cases, where its lead
rests mainly on 3 runs of one case (p = 0.10). As the skill README set out before the runs,
a tie means the honest recommendation is the reminder sentence, not this skill. The `-B`
probe line, its only consistent ungraded edge, could be tested as a one-line addition to
the reminder or to the shipped skill.

This held-out pair has now been used. Any v3 decided on these results needs a fresh
held-out pair. That pair should have headroom in its hidden tests: a case where the bare
model builds on a false claim. No counted run did that; only the gate's Sonnet run of
`stale-cents-comment` did.
