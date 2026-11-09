# Hygiene eval

This eval scores the `code-comments` hygiene skill
([purpose and limits](../../docs/skill/hygiene-skill.md)). Issue
[#45](https://github.com/AndrewGodlewsky/code-comments/issues/45) tracks it. Each case is
a small, realistic editing task aimed at one behaviour the skill claims. Each case is
run with and without the skill, and a script grades the outputs. That score is what
we hill-climb.

## The cases

Each case is in `cases/<name>/` and uses the layout that `claude plugin eval` reads:
`prompt.md` (the run settings, then the task), `case.yaml` (the expected outcome),
`graders/` (one statement per file) and `files/` (the repository the task starts
from). `references/<name>/` holds a hand-written good result for each case.

| Case | What it tests | The trap |
| --- | --- | --- |
| `retry-cap-elsewhere` | Keeping comments true away from the edit | The retry count changes in `config.py`, but the old count is also stated in a module docstring, a comment in `client.py` and `docs/operations.md` |
| `rename-stale-refs` | Renames | Comments, docstrings and a doc still name the old function after a rename |
| `comment-only-preserve` | Leaving good comments alone | Two comments are false. The licence header, a `noqa` directive and accurate comments must not change |
| `routine-edit-no-noise` | Restraint | Adding a simple `--quiet` flag needs no paragraph of comments |
| `capture-supported-reason` | Recording a reason that would otherwise be lost | The ticket explains why rows must be sorted; the code alone will not |
| `no-invented-reason` | Not inventing reasons | A timeout changes with no reason given. The skill should say so, not make one up |
| `change-contradicts-comment` | Stated limits | The user asks for 250 requests a minute, but a comment states the API's free-tier quota of 100 |
| `reason-only-in-test` | Moving a reason that would be lost | A simplification drops the code's shape, and the only reason for "last update wins" is a test comment |
| `clause-goes-stale` | Clause-level staleness | `parse_tags` stops raising on `None`; one clause of its docstring and a caller's comment go false |
| `issue-pointer-beside-reason` | Pointing to the issue behind a reason | Issue #212 records the finance vendor's two-decimal rule. The id belongs after the stated reason, never instead of it |
| `no-issue-tag-routine` | Not tagging routine work | Issue #318 asks for a `--limit` flag. The code should not gain an "added for #318" comment |

Every case scores preservation or restraint as well as the target behaviour. Round 1
of the tournament showed a skill can win on a proxy while doing harm: weaker models
given the skill rewrote valid comments. A change that raises one score by lowering
another is not an improvement.

## How grading works

`grade.py` holds one mechanical check per grader file, in the same order. The grader
text is what an LLM judge would see under `claude plugin eval`; the check answers the
same statement with code, so every iteration is scored the same way. Checks include:

- running the case's tests, or a short script that calls the edited code;
- comparing comment and docstring text before and after (from Python tokens and the
  AST, and from Markdown lines);
- comparing the code's AST with its docstrings removed, for "don't change any code";
- `scripts/stale_refs.py` for comments that name a removed function.

Some checks in `grade.py` are keyword heuristics: `reason_recorded`,
`last_wins_recorded`, `correction_recorded` and `no_invented_quota` read the added
comments; `reply_flags` and `reply_flags_conflict` read the reply. When a heuristic gets a run
wrong, record a human ruling in that run's `overrides.json`, as
`{"<grader text>": {"passed": true, "evidence": "why"}}`. The ruling and the original
check result both stay in the evidence.

## Running it

```sh
python evaluation/hygiene/grade.py --self-test        # references pass; inputs fail
python evaluation/hygiene/grade.py ITERATION_DIR      # grade every run, write grading.json
python evaluation/hygiene/grade.py RUN_DIR --case NAME
```

`tests/test_hygiene_eval.py` runs the self-test with the rest of the suite.
`scripts/lint_skills.py` treats the cases and references as eval text, so no skill
variant may copy an 8-word run from them.

An iteration follows the skill-creator layout:
`iteration-N/<case>/{eval_metadata.json, with_skill/run-K/, without_skill/run-K/}`,
each run holding `outputs/` (the edited repository and `RESPONSE.md`, the reply to
the user), `grading.json` and `timing.json`. The skill-creator scripts then build
`benchmark.json` and a review page. Results are kept in `iterations/`.

Each run is a Haiku subagent given a fresh copy of the case's `files/` and this
prompt (the second paragraph only for runs with a skill):

```text
You are working in the repository at <run>/outputs

Your first action must be to read <path>/SKILL.md in full. Then follow it.

The user's request:
<the task from prompt.md>

This is a self-contained exercise. Work only inside that repository directory, using
absolute paths. Do not read or change anything outside it, with one exception: reading
the SKILL.md named above is required and allowed even though it is outside the
repository, and do not use git, GitHub or any task tracking. When finished, write the
message you would send the user to RESPONSE.md in that repository directory.
```

For runs without a skill, the exception clause is left out. In iteration 5's reminder
arm, the request also ends with one sentence: "Keep code comments accurate: fix or
delete any comment, docstring or doc that your change makes false, and don't add
comments that only restate the code." Iteration 5 also ran every arm on Sonnet; its
agents were told to read this prompt from a file instead of receiving it inline.

## Limits

- **Triggering is not tested.** With-skill runs are told to read the skill file, so
  the eval measures what the skill does once loaded, not whether Claude picks it up.
- **Two models, one family.** Iterations 1 to 4 used Haiku subagents: cheap, and the
  weaker model is where Round 1 saw the skill do harm. Iteration 5 added Sonnet. No
  model outside the Claude family has been tried.
- **Small cases.** Each repository is a few files. They test single behaviours, not
  long work. The [pilot](../../docs/evaluation/pilot-report-2026-11-08.md) is the
  long-horizon test, and it found no downstream benefit.
- **The one-line reminder was tested only in iteration 5.** Iterations 1 to 4
  compared against a bare model. Iteration 5 added a one-sentence comment reminder,
  the kind of instruction the pilot found as good as the full skill downstream.
- **Few runs.** Two or three runs per configuration per case can show a large effect,
  not a small one.
- **The baseline still sees the repository's `AGENTS.md`.** Subagents inherit the
  worktree's project instructions. They hold workflow rules, not comment guidance, so
  the baseline is close to bare, but not bare.
- **A with-skill run can skip the skill.** In iteration 1 one with-skill run never
  opened `SKILL.md`. Check each with-skill transcript for the read, and exclude and
  re-run any that skipped it. The run prompt now makes reading the skill the first step.
  In iteration 3, two runs still refused: the prompt said "do not read anything outside
  it (apart from the file named above)", and they read that as forbidding the skill
  file. The prompt now says plainly that reading the skill is required and allowed.
- **The prose checks are text matches.** `lost_prose` treats a re-wrapped comment as
  kept when its words still appear in order. A paraphrase still counts as a loss;
  rule on it with an override.

## Iteration results

Each iteration's grades, timings, replies (`RESPONSE.md`) and edits (`changes.diff`,
against the case's `files/`) are in `iterations/iteration-N/`. Bulk outputs are not
kept. `benchmark.json` holds the analyst notes.

### Iteration 1 (2026-11-08): no difference

Haiku subagents, two runs per configuration, 24 runs.

| Case | With skill | Without skill |
| --- | --- | --- |
| `retry-cap-elsewhere` | 5/5, 5/5 | 5/5, 5/5 |
| `rename-stale-refs` | 5/5, 5/5 | 5/5, 5/5 |
| `comment-only-preserve` | 6/6, 6/6 | 6/6, 6/6 |
| `routine-edit-no-noise` | 4/4, 4/4 | 4/4, 4/4 |
| `capture-supported-reason` | 5/5, 5/5 | 5/5, 5/5 |
| `no-invented-reason` | 4/5, 4/5 | 4/5, 4/5 |

Both configurations pass 96.7% of checks. The skill adds about 2,000 tokens (5%) and
3 seconds per run.

- **The skill showed no gain over the bare model.** It did no harm either: every
  preservation and restraint check passed in all 24 runs.
- **Five cases are too easy.** Haiku without the skill already finds the distant
  references, the stale comments and the ticket's reason. They cannot show a gain.
- **One failure is shared by every run.** In `no-invented-reason`, no run invented a
  reason, but no reply told the user that none was given. The skill does not ask for
  that.
- **Grading changes during the iteration.** `lost_prose` falsely failed a run that
  re-wrapped a comment, and now accepts re-wrapping. One contaminated with-skill run
  was excluded (kept in `excluded-runs/`) and re-run.

Next: harder case variants, and a skill edit that asks the agent to tell the user
when a change it records has no stated reason.

### Iteration 2 (2026-11-08): one gain, one regression

The skill gained three lines: tell the user when a recorded change has no stated
reason; keep a stated limit the change breaks and report the conflict; look in tests,
callers and docs for a reason before simplifying. Three harder cases were added.
Configurations: the edited skill, the iteration-1 skill (`old_skill`) and no skill.
For the six iteration-1 cases, the old-skill and no-skill runs are reused from
iteration 1. Runs are told to read the skill first; every with-skill run did.

| Case | With skill | Old skill | Without skill |
| --- | --- | --- | --- |
| `no-invented-reason` | 5/5, 5/5 | 4/5, 4/5 | 4/5, 4/5 |
| `reason-only-in-test` | 4/6, 4/6 | 6/6, 5/6 | 4/6, 5/6 |
| `change-contradicts-comment` | 5/6, 6/6 | 6/6, 5/6 | 6/6, 6/6 |
| `clause-goes-stale` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| the other five | all pass | all pass | all pass |

Pass rates: with skill 95.4%, old skill 95.9%, without 95.0%. Time and tokens are
unchanged (about 21 seconds and 42,600 tokens per run).

- **The targeted gain held.** Both with-skill replies said the timeout change had no
  stated reason and asked for one. No other run did.
- **`reason-only-in-test` regressed.** Neither with-skill run moved the test's reason
  (the warehouse resends a SKU to correct a miscount, so the last update wins) into
  the docstring. Both said the behaviour was unchanged and left the docstring alone.
  One old-skill run recorded it. The new "look in tests" line did not produce the
  behaviour.
- **The stated-limit line may cause harm.** One with-skill run raised the limit to
  250 but left three statements that the client sends at most 100, saying they
  recorded the quota. The quota fact should stay; statements about what the code does
  must change.
- **`clause-goes-stale` cannot discriminate.** Every run fixed both stale clauses.
- **Grading changes.** `no_none_raises` falsely failed three runs that wrote "is not
  None and holds no tags", and now ignores "not None" (with a test). Two no-skill runs
  on `change-contradicts-comment` have overrides: one asked before changing anything,
  so the "100" statements stayed true; one asked the user to confirm the plan allows
  250, which does not claim it.

Next: make the skill record a reason found in a test when a simplification removes
the code's evidence of it, and separate an external stated fact (keep it) from a
statement of the code's own behaviour (update it).

### Iteration 3 (2026-11-08): the regression and the harm are fixed

The skill gained a line on rules a rewrite hides: when simplifying, write the rule and
its reason, found in a test, caller or doc, beside the new code. The limit line was
split: keep an outside fact (a vendor quota, a law), and update every statement of
what this code does. Configurations: the edited skill (v3), the iteration-2 skill
(`old_skill`, its runs reused) and no skill (iteration-2 runs reused). Every counted
with-skill run read the skill as its first tool call.

| Case | With skill (v3) | Old skill (v2) | Without skill |
| --- | --- | --- | --- |
| `reason-only-in-test` | 6/6, 5/6 | 4/6, 4/6 | 4/6, 5/6 |
| `change-contradicts-comment` | 6/6, 6/6 | 5/6, 6/6 | 6/6, 6/6 |
| `no-invented-reason` | 5/5, 5/5 | 5/5, 5/5 | 4/5, 4/5 |
| `clause-goes-stale` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| the other five | all pass | all pass | all pass |

Pass rates: with skill 99.1%, old skill 95.4%, without 95.0%. Tokens are unchanged
(about 42,700 per run). One with-skill run took 145 seconds against 17 to 27 for the
rest, which inflates the mean time; it is an outlier, not a cost of the skill.

- **`reason-only-in-test` improved.** Run 1 wrote the test's reason (the warehouse
  resends a SKU to correct a miscount) beside the simplified code. Run 2 recorded
  that the last update wins, but told the user it found no reason in the repository,
  though the test holds one. That run is a real failure; there is no override.
- **The stated-limit harm is gone.** Both runs changed every statement of the client's
  own limit to 250, kept the vendor's free-tier quota of 100, and told the user the
  two conflict. The replies were read by hand.
- **The `no-invented-reason` gain held.** Both with-skill replies said no reason was
  given.
- **Two runs were excluded** for the prompt wording described under Limits, and re-run.
  The excluded replies are in `excluded-runs/`.

On these cases the skill now beats the bare model on three behaviours and loses on
none. The gains are small, on two runs each, on Haiku, against a bare baseline.

Next: the one remaining failure is a run that searched for the reason and missed the
test. More runs of `reason-only-in-test` would show whether that is noise. The bigger
open questions are the Limits above: a one-line-reminder baseline, a stronger model,
and whether Claude loads the skill on its own.

### Iteration 4 (2026-11-08): issue pointers

The user asked for comments to point to the GitHub issue or PR behind the work, so a
later agent searching for that issue finds the code. The skill (v4) gained three lines:

- when a known issue or PR records the constraint, workaround or decision being
  written down, add its id after the fact as a pointer, never instead of it; a TODO,
  workaround or temporary hack gets the issue that tracks its removal, if known;
- do not tag code with the issue that changed it ("added for #N"), because that is
  history and commits hold it;
- never invent issue ids.

Two cases were added: `issue-pointer-beside-reason` (does the pointer appear, beside
the reason) and `no-issue-tag-routine` (does a routine change stay untagged).
Configurations: v4, the iteration-3 skill (`old_skill`, v3) and no skill. The v4 runs
are new on all eleven cases. The v3 and no-skill runs are new on the two new cases and
reused from iteration 3 on the other nine. Every v4 run read the skill first.

| Case | With skill (v4) | Old skill (v3) | Without skill |
| --- | --- | --- | --- |
| `issue-pointer-beside-reason` | 5/6, 6/6 | 5/6, 4/6 | 3/6, 3/6 |
| `reason-only-in-test` | 4/6, 6/6 | 6/6, 5/6 | 4/6, 5/6 |
| `no-invented-reason` | 5/5, 5/5 | 5/5, 5/5 | 4/5, 4/5 |
| `change-contradicts-comment` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| `clause-goes-stale` | 6/6, 6/6 | 6/6, 6/6 | 6/6, 6/6 |
| `no-issue-tag-routine` | all pass | all pass | all pass |
| the other five | all pass | all pass | all pass |

Pass rates, as the mean of each run's rate: with skill 97.7% (115 of 118 checks in
total), old skill 97.0% (114), without 91.4% (107). The no-skill rate fell from 95.0% because the new pointer case is hard
for it. Tokens: about 43,000 per run with either skill and 40,400 without. New v4 runs
took 15 to 29 seconds.

- **The pointer works.** Both v4 runs cited #212 beside the vendor's rule; no v3 or
  no-skill run cited it. The best run added one comment and a fix:

  ```diff
       """Return value formatted for the export file."""
  -    return str(value)
  +    # The finance vendor's importer rejects the whole file unless every amount
  +    # matches ^\d+\.\d{2}$, and it cannot be changed (issue #212).
  +    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
  ```

- **Docstring rewrites are the common failure on the pointer case.** v4 run 1, v3
  run 2 and both no-skill runs rewrote the accurate docstring "Return value formatted
  for the export file." The no-skill runs also wrote more comment lines than the
  case allows, and recorded the reason without the issue.
- **`no-issue-tag-routine` does not discriminate.** No run in any configuration tagged
  the code with #318. The case guards the new rule against harm; it shows the rule
  causes no tagging, not that the rule prevents it.
- **`reason-only-in-test` dipped.** v4 run 1 simplified the code, added no comment,
  and told the user it found no reason, though the test holds one. Run 2 passed every
  check. Iteration 3's run 2 failed the same way, so this looks like run-to-run
  variance on a search Haiku sometimes skips, not a cost of the new lines. Watch it.
- **Two stray files were deleted** before grading: a helper script that v4 run 2 of
  `reason-only-in-test` wrote outside the repository, and a check folder from no-skill
  run 1 of `no-issue-tag-routine`. Neither affected the grade. `benchmark.json` notes
  both.

The pointer behaviour is a clear gain on its one case (2 of 2 runs against 0 of 4).
The usual caveats apply: two runs each, Haiku only, a bare baseline, triggering
untested, and one case per new behaviour. The `issue-pointer-beside-reason` case gives
the issue in the request; a case where the issue id appears only in a TODO or a linked
doc would test the rule further.

Next: more runs of `reason-only-in-test` and the pointer case, and the open Limits
above.

### Iteration 5 (2026-11-08): the skill against a one-line reminder

Issue [#46](https://github.com/AndrewGodlewsky/code-comments/issues/46). The pilot
found that one general sentence did as well as the full skill downstream, so this
iteration asks whether the skill beats one comment-specific sentence on these cases,
and whether the result holds on a stronger model. The skill is unchanged (v4). Arms:

- **Skill v4.**
- **Reminder:** no skill; the request ends with "Keep code comments accurate: fix or
  delete any comment, docstring or doc that your change makes false, and don't add
  comments that only restate the code."
- **No skill.**

Haiku ran three runs per arm per case. Its skill and no-skill runs 1 and 2 are the
iteration-4 runs, reused unchanged; everything else is new. Sonnet ran two new runs
per arm per case. Sonnet agents read the prompt from a file; Haiku agents got it
inline, with the same text. Results are in `iterations/iteration-5-haiku/` and
`iterations/iteration-5-sonnet/`.

| Model | Skill v4 | Reminder | No skill |
| --- | --- | --- | --- |
| Haiku (33 runs per arm) | 97.5% | 90.6% | 91.1% |
| Sonnet (22 runs per arm) | 97.4% | 94.4% | 93.3% |

Pass rates are the mean of each run's rate. The skill cost about 6% more tokens on both
models (Haiku about 43,200 per run against 40,800 and 40,500; Sonnet 40,700 against
38,200 and 38,300).

Cases where the arms differed (checks passed per run):

| Case | Model | Skill v4 | Reminder | No skill |
| --- | --- | --- | --- | --- |
| `no-invented-reason` | Haiku | 5/5, 5/5, 5/5 | 4/5, 4/5, 4/5 | 4/5, 4/5, 4/5 |
| | Sonnet | 5/5, 5/5 | 4/5, 4/5 | 4/5, 4/5 |
| `issue-pointer-beside-reason` | Haiku | 5/6, 6/6, 4/6 | 3/6, 3/6, 3/6 | 3/6, 3/6, 2/6 |
| | Sonnet | 6/6, 5/6 | 5/6, 5/6 | 6/6, 5/6 |
| `change-contradicts-comment` | Haiku | 6/6, 6/6, 6/6 | 5/6, 6/6, 5/6 | 6/6, 6/6, 6/6 |
| | Sonnet | 6/6, 6/6 | 6/6, 5/6 | 5/6, 6/6 |
| `reason-only-in-test` | Haiku | 4/6, 6/6, 6/6 | 5/6, 4/6, 5/6 | 4/6, 5/6, 5/6 |
| | Sonnet | 6/6, 6/6 | 6/6, 4/6 | 5/6, 5/6 |
| `retry-cap-elsewhere` | Sonnet | 5/5, 5/5 | 5/5, 5/5 | 4/5, 5/5 |
| `capture-supported-reason` | Sonnet | 4/5, 4/5 | 5/5, 5/5 | 4/5, 5/5 |

Every other case passed every check in every run of every arm.

- **The skill beats the reminder on both models.** On Haiku the reminder did no
  better than no skill at all. On Sonnet it added about one point. The skill's margin
  over the reminder is about 7 points on Haiku and 3 on Sonnet.
- **Reporting a missing reason is the clearest gain.** Every skill run told the user
  no reason was given for the timeout change; no reminder or no-skill run did, on
  either model. One Haiku reminder run wrote no reply on this case.
- **Issue pointers help Haiku, not Sonnet.** On Haiku, every skill run cited #212
  beside the vendor's rule and no other run did; reminder runs never stated the vendor
  reason either. On Sonnet, three of the four runs without the skill cited #212. In
  every arm, the common failure on this case is rewriting the accurate docstring
  "Return value formatted for the export file."
- **The reminder can delete a true comment.** On `change-contradicts-comment`, two
  Haiku reminder runs and one Sonnet reminder run deleted the vendor's free-tier quota
  of 100 requests a minute, which stayed true. "Fix or delete any comment your change
  makes false" may have encouraged it. The skill kept the quota in every run.
- **Comment length is where the reminder did best.** No reminder run went over a
  case's comment-line limit. On `capture-supported-reason`, both Sonnet skill runs and
  one Sonnet no-skill run added more than the limit of four. On
  `issue-pointer-beside-reason`, Haiku skill run 3 and all three Haiku no-skill runs
  added five lines against a limit of four.
- **Five cases still do not discriminate** on either model: `clause-goes-stale`,
  `comment-only-preserve`, `no-issue-tag-routine`, `rename-stale-refs` and
  `routine-edit-no-noise`.
- **Grading change.** `grade.py` now skips tool caches (`.pytest_cache`,
  `.mypy_cache`, `.ruff_cache`). One Haiku no-skill run had run pytest, and the
  README that pytest writes into its cache was counted as added comments. That run
  gained one check; no other score changed.
- **Runs were not fully sandboxed.** In every arm, some runs wrote scratch files
  outside their repository. Grading reads only the repository, so scores are unaffected.

The skill earns its place on these cases: it beats a comment-specific one-line reminder
on both models, by doing things the reminder does not ask for (report a missing reason,
keep outside facts, point to the issue). The gain is small on Sonnet, where the bare
model is already strong. The caveats stand: small cases, few runs, one model family,
reused Haiku runs, different prompt delivery per model, and triggering untested. The
downstream pilot, where the skill did not beat a general sentence, is a separate
question this eval does not answer.

Next: test triggering with `claude plugin eval` (needs an approved spending cap), and
watch comment length, where the skill and no-skill runs went over and the reminder
did not.
