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

Two checks are heuristics: `reason-recorded` (keywords near the sort) and
`reply-flags-missing-reason` (keywords in the reply). When a heuristic gets a run
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

## Limits

- **Triggering is not tested.** With-skill runs are told to read the skill file, so
  the eval measures what the skill does once loaded, not whether Claude picks it up.
- **One model.** Runs use Haiku subagents: cheap, and the weaker model is where
  Round 1 saw the skill do harm. A result on Haiku may not hold on a stronger model.
- **Small cases.** Each repository is a few files. They test single behaviours, not
  long work. The [pilot](../../docs/evaluation/pilot-report-2026-11-08.md) is the
  long-horizon test, and it found no downstream benefit.
- **The without-skill baseline is a bare model**, not the one-sentence instruction
  the pilot compared against. A skill that beats the bare model here may not beat a
  one-line reminder.
- **Few runs.** Two runs per configuration per case can show a large effect, not a
  small one.

## Iteration results

None yet.
