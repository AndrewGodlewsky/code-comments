# verify-before-relying

**Status: evaluated. It does not beat the one-line reminder.** Over 165 graded runs on
Claude Haiku and Sonnet, the skill ties the reminder sentence in
[eval/arms.json](eval/arms.json) on every graded check (after an auditor agent's rulings),
in training and on the held-out cases. It beat the shipped `code-comments` skill only on
Haiku's training cases (96/96 against 90/96, half the gap in one case), and tied it on
Sonnet and on the held-out pair. As this README said before the runs, a tie means the
honest recommendation is the sentence, not this skill. Results are in
[eval/RESULTS.md](eval/RESULTS.md), and the samples are small (see Limits).

An incubator skill for issue [#50](https://github.com/AndrewGodlewsky/code-comments/issues/50),
from ideation candidate C2 ([candidates](../ideation/2026-11-11-candidates.json)). The
installable skill is [skill/verify-before-relying/SKILL.md](skill/verify-before-relying/SKILL.md).
The sources and how they shaped each rule are in [research.md](research.md). The eval
cases are described in [eval/CASES.md](eval/CASES.md).

## The problem

Your code carries comments, docstrings and docs that say what it does. Some of them are
wrong, because the code changed and the text did not. That is the two-sources-of-truth
drift this project exists to remove ([intent.md](../../intent.md)).

The damage happens when an agent writes **new** code that depends on one of those
sentences: a value's units, a helper's rounding, what a function returns on bad input,
the error it raises. The quickest path is to believe the text. The new code then builds
on behaviour that does not exist. It passes review because it matches the comment, and
it fails at run time.

The opposite mistake is just as real. "The code is the truth, so make the text match"
also erases the sentences that are right when the code is wrong: a requirement the code
breaks, or a fact about a vendor. In the hygiene eval, a one-line "fix what is false"
reminder deleted a true vendor quota in 3 of 5 iteration-5 runs. The bare model and the
shipped skill kept it every time (re-counted from
`evaluation/hygiene/iterations/iteration-5-*/change-contradicts-comment/*/run-*/grading.json`).

Evidence that this happens (details and limits in [research.md](research.md)):
- Misleading comments and hints cut model accuracy on code tasks, in most studies more
  for the weaker model (CodeCrash: Claude 3.5 Haiku -27.5% / -53.3%, Sonnet -14.4% /
  -43.4%). These are single prompts on 2024-era models.
- Noticing is not acting. In Xu and Wu, Claude Code named the conflict between a stale
  instruction file and the code in 79 of 80 runs, and followed the file anyway. Codex
  rewrote working code to match the file in 20 of 80 runs, and the tests then failed in 17.
  Those files were auto-loaded instructions; comments and docstrings arrive as tool
  output, so the effect may be smaller here.

## What it adds over the shipped skill

The shipped [`code-comments` skill](../../plugins/code-comments/skills/code-comments/SKILL.md)
keeps comments true after the agent's own change. It already says "Treat existing
comments as claims. Check them against the code, tests and task", "Take the intended
contract from evidence of intent", and keep an outside fact as written. Large overlap is
expected.

This skill acts at a different moment: **before** new code is built on a claim, and on
what gets built rather than on comment text. It adds five things the shipped skill does
not say:
1. **Check before building.** Name the claims the new code will depend on, and check only
   those, against the body and its tests.
2. **Follow the helper.** Read a named helper's body in its own file, look up library
   defaults the body leaves implicit, and run a throwaway probe from the shell when it is
   still unclear.
3. **Sort the conflict by the kind of claim.** A description of the code loses to the
   code and is corrected. A requirement or outside fact keeps its words, and the
   conflict is reported. This also covers a request to bring a doc in line with the code.
4. **Correct the user's premise.** When the request repeats a false claim, deliver what
   the user wants and say first that the premise is wrong, where the false text is, and
   what the code really does.
5. **Trust a true claim.** No defensive conversion, no guard for a case the claim rules
   out, no confirmation question, and the text stays word for word.

It asks for no new comments beyond corrections. How a correction is worded follows the
shipped skill.

## When to use it, and when not

Use it when:
- the code you are about to write calls, extends or reuses existing code, and depends on
  a stated detail of it: units, rounding, ordering, return shape, the value returned on
  failure, the errors raised;
- the request tells you to use a named helper, or repeats what a docstring or doc says;
- you are asked to bring a doc in line with the code.

Leave it out for:
- keeping comments true after your own edit. That is the shipped skill's job;
- auditing every comment in a file or repository. It checks only claims the new code
  relies on;
- instruction files (`AGENTS.md`, `CLAUDE.md`) and decision records. Those are the user's
  layers ([intent.md](../../intent.md), scope clarification). The skill reports a
  conflict with them and leaves them as they are.

## How it works

Instructions only: a `SKILL.md` with a 94-line body and no scripts. It reads the code each
time and stores nothing. It has no index, generated docs view, memory store or lookup service
([ADR 0001](../../docs/adr/0001-context-lives-inline-no-central-index.md)). The probe is
one shell call, such as `python -B -c` (`-B` stops Python writing bytecode caches), and
leaves no files behind.

The rules, in the order the agent meets them:
1. **Find the load-bearing claims**: the ones the new code depends on.
2. **Check each against what runs**: the body, the helpers it calls, the tests,
   library defaults, and a probe if still unclear.
3. **Build on what the code does.** A true claim is trusted. A false one is built
   around, as the tests pin the behaviour. A pinned helper that does not fit keeps what
   its callers get: the need is met beside it, or the helper is extended so that existing
   calls behave as before.
4. **Settle a conflict by kind.** A description is corrected. A requirement or outside
   fact is kept and reported. The code changes to meet it only when the task is to fix
   that behaviour; when the user asked for the behaviour that breaks it, the change is
   made as asked and the conflict reported, as the shipped skill says.
5. **Report** each false claim by its file and the function, constant or heading it sits
   in, putting a false premise from the request first. A claim counts as the user's
   premise only when the request itself states it. (v1 asked for `file:line`; v2 dropped
   that after it produced impossible line numbers, see
   [eval/CHANGES.md](eval/CHANGES.md).)

Two rules are marked *judgement* in the skill because no source supports them: treating
lowercase "must" as a requirement (RFC 8174 limits that meaning to capitals), and
treating a sentence that mixes a description with a requirement as a requirement, kept
as written. No rule, marked or not, has been shown to improve results over the one-line
reminder; [research.md](research.md) labels most of the others hypotheses too.

## Its eval

Seven cases in [eval/](eval/): five training and two held out. Three cases have a false
claim. Three are twins with the same request and a true claim, which catch distrust the
skill itself could cause. The seventh is a docs sync with mixed claims.

| Case | Split | Claim |
| --- | --- | --- |
| `stale-cents-comment` | training | false unit comment; the contradicting evidence is mainly in a test |
| `true-cents-comment` | training | its true twin |
| `request-quotes-stale-docstring` | training | the request repeats a half-true docstring |
| `request-quotes-true-docstring` | training | its true twin |
| `docs-sync-keeps-requirements` | training | a doc mixing stale descriptions, a requirement and a vendor fact |
| `helper-docstring-lies` | held out | the request names a helper whose docstring misstates its rounding |
| `helper-docstring-true` | held out | its true twin |

The held-out pair uses material no training case uses. Apart from the library-default
line, the rules it needs are exercised by training cases, so it can show whether tuned
rules carry over to new material. The split was swapped
before any run: the request pair, held out at first, was the only pair to use the
"request carries the claim" section, so it could not detect overfitting.

The core checks are hidden behavioural tests on the new code wherever there is new code,
plus text checks on corrected descriptions and kept requirements. Preservation and
restraint use AST comparison and byte identity, and every case with new code checks for
stray files such as a leftover probe. Reply checks are keyword heuristics, and every
case has at least one core check, so a reply check cannot carry a case on its own.

There are four arms:
- `with_skill` reads this `SKILL.md` first.
- `shipped_skill` reads the shipped `code-comments` skill first. It decides whether this
  is a new skill or only a variant of the shipped one (#21, #48).
- `reminder` adds one sentence from [eval/arms.json](eval/arms.json) to the request. The
  sentence carries the skill's whole gist: check the claim, follow the code, correct
  descriptions, keep requirements and outside facts, and report. If it ties the skill,
  the honest recommendation is the sentence.
- `without_skill` gets the request alone.

Commands, from the repository root:

```sh
python incubator/harness.py self-test verify-before-relying   # references pass, inputs fail
python incubator/harness.py lint verify-before-relying        # format, portability, no copied case text

# 1. Gate: bare model only, for case selection (the gate here ran all seven cases)
python incubator/harness.py prepare verify-before-relying --iteration gate-haiku --arms without_skill --runs 2
#   ...give each prompt in eval/iterations/<name>/runs.json to a fresh agent of the chosen model...
python incubator/harness.py grade verify-before-relying --iteration gate-haiku

# 2. All four arms on the training cases; after a skill edit, re-run with_skill only
python incubator/harness.py prepare verify-before-relying --iteration iteration-1-haiku --runs 3 --split train
python incubator/harness.py grade verify-before-relying --iteration iteration-1-haiku
python incubator/harness.py verify-reads verify-before-relying --iteration iteration-1-haiku TRANSCRIPT_DIR
python incubator/harness.py prepare verify-before-relying --iteration iteration-2-haiku --arms with_skill --runs 3 --split train

# 3. Held-out pair, once, after the last skill edit
python incubator/harness.py prepare verify-before-relying --iteration heldout-haiku --runs 3 --split held-out
python incubator/harness.py grade verify-before-relying --iteration heldout-haiku

python incubator/harness.py summary verify-before-relying iteration-1-haiku iteration-1-sonnet iteration-2-haiku iteration-2-sonnet heldout-haiku heldout-sonnet
```

Each step was repeated with a `-sonnet` iteration (2 runs per cell; 1 for the gate).
`verify-reads` lists any skill-arm run that edited before reading its skill; exclude and
re-run those. Model runs cost money, and each campaign needs the user's approval first
([intent.md](../../intent.md), "Decisions still open").

## Results

Mean pass rate and checks passed, after the rulings. Full tables, per-case results and
the rulings are in [eval/RESULTS.md](eval/RESULTS.md); the reasoning is in
[eval/ANALYSIS.md](eval/ANALYSIS.md).

| Iteration | Skill | with_skill | shipped_skill | reminder | without_skill |
| --- | --- | --- | --- | --- | --- |
| Training, Haiku (3 runs per cell) | v1 | 100.0%, 96/96 | 93.9%, 90/96 | 100.0%, 96/96 | 86.7%, 82/96 |
| Training, Sonnet (2 runs per cell) | v1 | 100.0%, 64/64 | 100.0%, 64/64 | 100.0%, 64/64 | 95.4%, 61/64 |
| Training, Haiku, `with_skill` re-run | v2 | 100.0%, 96/96 | | | |
| Training, Sonnet, `with_skill` re-run | v2 | 100.0%, 64/64 | | | |
| Held out, Haiku | v2 | 100.0%, 36/36 | 100.0%, 36/36 | 100.0%, 36/36 | 97.2%, 35/36 |
| Held out, Sonnet | v2 | 100.0%, 24/24 | 100.0%, 24/24 | 100.0%, 24/24 | 91.7%, 22/24 |

What the numbers say:
- **A tie with the reminder.** The sentence matched the skill on every graded check in
  every iteration that ran both. Before the auditor's rulings, it scored one check higher
  on Haiku's training cases (95/96 against 94/96).
- **A narrow lead over the shipped skill, on one model.** On Haiku's training cases the
  shipped skill noticed the real error in `request-quotes-stale-docstring`, built only the
  None check and asked permission for the rest (hidden tests 0/3, against 3/3 for the
  skill). It also damaged the synced doc in 2 of 3 runs. On Sonnet and on the held-out pair
  the shipped skill scored 100%.
- **The hidden tests never favoured the skill over the bare model.** The bare model built
  correct new code in every run of every case with hidden tests (training 20/20, held out
  10/10). Of the 20 checks the skill gained over the bare model, 18 are text checks: it
  corrected false descriptions (15 of 15 runs against 4 of 15) and kept a requirement and
  a vendor fact in the doc sync (privacy 5/5 against 2/5, quota 5/5 against 1/5). The
  other two are one preservation and one reply check in Haiku's doc sync. The reminder did
  the same.
- **The held-out pair showed no loss and no lead.** v2 scored 100% on new material, with no
  over-distrust of the true twin. So did the shipped skill and the reminder.
- **Ungraded, the skill's one consistent edge over every other arm is no bytecode
  caches.** `with_skill` left them in 0 of 60 runs; every other arm left them in most runs
  (78 of 105). Its probe line says to run `python -B`, and its iteration-1 runs did
  ([eval/ANALYSIS.md](eval/ANALYSIS.md)). Whether that line alone would do it is untested.
  The graders skip caches by design.
- **Ungraded, v1's reply rules caused harm, and v2 fixed most of it.** v1's `file:line`
  demand produced 112 line citations, 5 of them past the end of the file. v2 has none. v1
  called a comment's claim "the premise" in 5 of 10 runs of the cents cases; v2 still did in
  2 of 10.

## Limits

Of the eval:
- **Few runs.** 2 or 3 runs per cell detect only large effects: 3/3 against 0/3 has a
  two-sided Fisher exact p of 0.10, and 2/2 against 0/2 has 0.33. Three arms sit at the
  ceiling in most cells, so the eval cannot rank them. A gap smaller than one failed run
  in 15 would not show.
- **Small fixtures.** Seven small Python cases of a few files each. In a real repository
  the claim and the evidence against it can sit much further apart.
- **One model family.** Claude Haiku and Sonnet only.
- **Cases built by agents.** Every case, reference and hidden test was written by an
  agent. None comes from a real repository or a user's report.
- **Rulings made by an agent.** An auditor agent, not a human, made all seven rulings. Four
  of them moved `with_skill` runs from fail to pass, and the tie with the reminder depends
  on them (before them the reminder led by one check on Haiku).
- **Reply checks are keyword heuristics** with known gaps. The cents reply check passes a
  reply that reports the conflict but does not say which side is right. The false-alarm
  check misses a negation more than three words away. The quota reply check only looks for
  its keywords anywhere in the reply. Details in [eval/RESULTS.md](eval/RESULTS.md).
- **Gate-based case selection.** A bare-model gate ran first on all seven cases, the
  held-out pair included, and the request pair was hardened afterwards to leave room for a
  gain ([eval/GATE.md](eval/GATE.md)). That favours cases where the bare model falls
  short, which can widen the gap over the bare model. It does not favour the skill over the
  reminder or the shipped skill. GATE.md planned to re-run the gate on the hardened pair
  before the other arms; that re-run did not happen. In the counted runs the bare model
  still passed the pair's hidden tests 10/10 (5/5 in each case).
- **Prompt read from a file.** The agents read their task from a prompt file instead of
  receiving it as a user's message, which is not how real requests arrive.
- **Activation is untested.** The eval tells the agent to read the skill first, so it says
  nothing about whether the description makes the skill load on its own. On its own, the
  shipped skill loaded in 0 of 18 Haiku and 3 of 18 Sonnet runs, and requests rarely say
  "check the docstring".
- **The hidden tests had no headroom.** The bare model built correct new code in every
  counted run of every case. So the eval never tested the skill's central claim, that it
  stops new code being built on a false claim, in a setting where the bare model fails.
  The gate's one run that built on a false claim (Sonnet in `stale-cents-comment`) did not
  recur.
- **The held-out pair is spent.** It was run once, on v2. It cannot judge a later version.

Of the skill:
- **Building on the code can be programming by coincidence.** The Pragmatic Programmer
  says to rely only on documented behaviour. When no test pins the behaviour, the skill
  asks the agent to state its assumption. That reports the risk; it does not remove it.
- **Paranoia is a possible cost, not seen here.** Most claims are true (CASCADE: 814
  consistent pairs to 71 inconsistent ones). Every run of the three true twins passed in
  every arm, one `with_skill` run only by ruling (v1, `iteration-1-haiku`
  `true-cents-comment` run-2, false-alarm check 06). The twins measure over-distrust only
  on these three requests.
- **The library-default rule changed no outcome.** `helper-docstring-lies` rests on
  Decimal's half-even default, but every arm found it through the visible test that pins
  it.
- **Sorting claims by wording is a heuristic.** Real docs mix description and requirement
  in one sentence. The mixed-sentence rule (*judgement*) kept a false description in the
  synced doc in every `with_skill` run.
- **Cost.** Tokens were not measured. `with_skill` replies ran 15 to 19% longer than the
  bare model's on the training cases, and 32% longer on Haiku's held-out cases. On
  Sonnet's held-out cases they were the shortest of the four arms.

## Next steps

The gate, the four-arm run, the noticed-but-followed count and the held-out run are done.
In order:

1. **Put the deliverable to the user.** The data supports recommending the reminder
   sentence in [eval/arms.json](eval/arms.json), not this skill. Record it as a variant
   finding for #21 and #48: the shipped skill tied this skill on Sonnet and on the held-out
   pair. Do not move the skill into a plugin unless the user decides otherwise.
2. **Report the shipped-skill result to its owners.** On Haiku in
   `request-quotes-stale-docstring`, the shipped skill noticed the real ValueError, built
   only the None check and asked permission (hidden tests 0/3; the bare model passed 3/3).
   The run folders are `eval/iterations/iteration-1-haiku/request-quotes-stale-docstring/shipped_skill/run-{1,2,3}/`.
   The cause, its scope and ask-first guidance, is a hypothesis. Test it with a targeted
   eval of the shipped skill before changing it.
3. **Test the `-B` line on its own.** It is the skill's only consistent edge over every
   other arm. First ask the user whether bytecode caches should count as stray files; the
   graders skip them for every incubator skill (`gradelib.SKIP_DIRS`). If they should, run
   the reminder with one added sentence about `python -B` against `with_skill`.
4. **Fix the reply heuristics in `eval/grade.py`.**
   - `stale-cents-comment` 06: read the sentence before the quote too; accept "say
     otherwise" and "a false description"; stop counting "really"; and fail a reply that
     reports the conflict without saying which side is right.
   - The `06` false-alarm checks: count a sentence-initial negation ("No claims ... were
     false").
   - `docs-sync-keeps-requirements` 08: require 250 and 100 in one sentence that compares
     them.

   Then run `self-test`, re-grade every iteration, and check that each `overrides.json`
   still agrees with its check or can be removed.
5. **Build cases with hidden-test headroom before any more skill edits.** Only a case where
   the bare model builds on a false claim can test the skill's main claim. Candidates are
   the reserve cases in [eval/CASES.md](eval/CASES.md) and the hardening option for
   `helper-docstring-lies` in [eval/GATE.md](eval/GATE.md) (move the half-even pin into a
   ledger test). Gate each on the bare model and keep only those with hidden-test failures.
   Build a fresh held-out pair, since this one is spent.
6. **Settle "premise".** v2 still calls a comment's claim "the premise" in 2 of 10 Haiku
   runs of the cents cases. All 5 held-out `with_skill` replies use it for a claim the
   request implies but does not state. Decide whether an implied claim counts, then reword
   the rule or drop the word.
7. **Settle two policy questions with the user:** whether to correct an unasked-for false
   docstring or only report it (the bare model left a false description in place in 11 of
   15 runs, and reported the conflict in each of them), and whether a sentence mixing a
   description with a requirement should stay whole.
8. **Before any shipping decision**, run an activation eval on the description, run 5 or
   more runs per cell, and add a model outside the Claude family.
