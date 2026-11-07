# Hill-climbable evals for the Code Comments skill

Status: proposed eval design with an offline harness and a draft, synthetic seed
case set. No skill exists yet and no model has been run. The case set and grading
method still need the user's sign-off (below) before any number steers changes.

This plan adapts the build-eval, eval-audit and eval-hillclimb guides shipped with
Anthropic's `claude-api` skill to this repository. Those guides define an eval as
inputs, a way to run the system on each input, and a way to grade each output.
They also require two human sign-offs (inputs, grading), oracle/null checks before
paid runs, and a train/test split before any hill-climb. The
[evaluation protocol](../research/evaluation-protocol.md) remains the canonical
research design. This document covers the faster loop used to *develop* the skill.

## Two tiers: score downstream, guard with the proxy

**Rescoped 2026-11-07.** This plan first made `comment-edit` the hill-climb target.
That was a mistake: it measures the comment *writer*, while the product goal
(see `intent.md`, "The user's fuller theory") is a *later*, possibly weaker,
agent making correct changes. The primary score is now the downstream tier.

| Tier | Question | Cost per round | Role |
| --- | --- | --- | --- |
| **Downstream sequence eval (#19)** | Writer: whichever context-maintenance arm is being tested (none, docs folder, inline skill variant). It makes each change in a sequence. A *fresh, weaker reader* with no access to the writer's session or evidence then makes the follow-up change. Is the reader's change correct, are constraints preserved, and do the docs or comments drift? | Several agent sessions per case | **Primary score.** Variants are chosen and climbed on this |
| **Writer guardrail: `comment-edit`** | After an agent edits code with the skill, do the files contain the required explanation in the right place, without stale or unsupported claims, collateral damage or noise? | One agent session per case; grading is programmatic and free | Cheap check before any downstream spend. A variant that invents reasons, leaves comments false or rewrites valid comments is rejected here. Not optimised directly |

The proxy's noise budget encodes "leaner is better" a priori. Climbing it could
favour terse comments that do not help weaker readers, which only the downstream
tier can see.

## The `comment-edit` flow

**Entry point (system under test):** a coding agent with the skill installed is
given an isolated copy of a case's `visible/` directory and its `TASK.md`. The
agent edits the workspace. The skill is the only variable between variants.
Model, harness, tools, budgets and case files stay fixed.

**Input per case:** a small repository snapshot, a task request, and any evidence
a real developer would have (a ticket, a design note, a reviewer comment). The
evidence is agent-visible. That matches the protocol's rule that the writer may
use contemporaneous evidence, not hidden tests or future requests.

**Grader-only material** lives under each case's `private/` directory: the fact
ledger, anchor phrases, protected comments, hidden behavioural checks and a
reference end state. The runner copies only `visible/` into the agent workspace.
That keeps answers out of the working directory, but an agent with a shell could
still read this repository by absolute path. A live adapter (#18) must run in an
isolated copy with no route back here (#7). The cases are also public in Git, so
the seed set must never be presented as held-out.

### Case families (`tags[0]`)

The families keep the eval two-sided. A skill that comments everything fails
`restrain`. A skill that never comments fails `capture`.

| Family | What the agent faces | Correct outcome |
| --- | --- | --- |
| `capture` | A code change whose evidence contains non-obvious rationale or constraints | Behaviour correct; each required fact explained in its owning scope; no unsupported rationale invented |
| `maintain` | Existing comments, some of which the requested change makes false | Behaviour correct; stale claims removed or revised; still-valid comments kept; new facts added |
| `restrain` | A routine change with no non-obvious knowledge in the evidence | Behaviour correct; no explanatory noise added |
| `audit` | A comment-only request ("refresh the comments in this module") on code with stale or missing explanation | Code semantics unchanged; stale claims fixed; protected comments intact |

### Metrics

Every metric is defined on every case, so one grade dictionary covers all families.

| id | kind | Meaning |
| --- | --- | --- |
| `pass` | binary, **headline** | All of the conditions below hold: `behavior`, full `recall`, zero `bad_claims`, full `preserved`, `noise_lines` within the case budget |
| `behavior` | binary | Hidden checks pass (`capture`/`maintain`/`restrain`), or the module's AST is unchanged apart from docstrings (`audit`) |
| `recall` | float | Required facts explained within their owner's scope, divided by required facts (1.0 when none are required) |
| `misplaced` | count, lower is better | Required facts explained only outside their owner's scope |
| `bad_claims` | count, lower is better | Forbidden claims present: stale facts and plausible-but-unsupported rationale planted in the evidence as rejected |
| `preserved` | float | Protected comments (license, tool directives, still-valid rationale) still present |
| `noise_lines` | count, lower is better | New comment/docstring lines not excused by a required fact. A block explaining a fact excuses up to 4 new lines per fact it explains; unchanged lines never count |

The offline grader decides whether a fact is present with **anchor groups**: every
group must match at least one alternative inside a single comment block or
docstring. This is a cheap, deterministic proxy for "the fact is explained". It
errs in both directions. Paraphrase can produce a false negative. A correct remark
that mentions a refuted idea ("not a CDN issue") can trigger a false-positive bad
claim. Keyword stuffing can produce a false positive fact.

Each ledger entry carries probe sentences that the self-test enforces: paraphrases
a fact must accept (`also_matching`) and correct remarks a forbidden claim must not
flag (`not_matching`). Add a probe whenever a reviewed answer is misgraded. Noise
and bad-claim penalties make stuffing expensive. A calibrated rubric judge (#17)
is the planned semantic check. Treat anchor scores as a development signal until
that judge agrees with human labels.

### Known grader limitations

These are recorded so a hill-climb does not mistake them for skill behaviour:

- **Moved or reworded comments.** A comment moved verbatim is free, but rewording
  it while moving it counts its lines as new noise.
- **Correcting versus deleting.** Each removed stale line (one matching a
  forbidden claim) pays for one replacement line, so a same-length correction
  costs no more than deletion. A longer correction still spends noise budget.
- **Adjacent comments merge into one block.** A fact can be satisfied by words
  from a neighbouring comment, and nearby padding can be excused, within the
  per-fact cap.
- **Untouched files.** Editing a file the task says to leave alone is not
  penalised unless it breaks behaviour.
- **Audit reformatting.** `audit` cases compare ASTs, so pure reformatting of code
  during a comment-only request is not detected.
- **Process isolation only.** Hidden checks run in a separate process with a random
  result token. Workspace code that crashes, exits or renames an API scores
  `behavior` 0; it is not dropped as a grader error. This is still not a sandbox.

### Grader validation (runs offline, no model calls)

Per eval-audit section 2, the harness ships with adapters that must produce known
scores before any paid run. `python -m evaluation.skill_eval.run selftest` runs all of them:

| Adapter | Produces | Expected |
| --- | --- | --- |
| `oracle` | The reference end state | `pass` = 100% |
| `null` | The untouched workspace | `pass` = 0% |
| `strip` | Reference code with every comment and docstring removed | `capture`/`maintain`/`audit` fail (recall or preserved); `restrain` may pass |
| `spam` | Reference plus a restating comment above every statement | Fails the `noise_lines` budget everywhere |
| `stale` | Reference plus every forbidden claim as a comment | `bad_claims` > 0 everywhere a forbidden claim exists |

A case that the oracle cannot pass, or that a degenerate adapter passes, is a
broken case. The self-test fails loudly instead of averaging it in.

## Hill-climb protocol (once a skill and a live adapter exist)

> Since the 2026-11-07 rescope, this protocol applies to the **downstream** score
> (#19). `comment-edit` still runs every round as a guardrail with the same
> mechanics, but no change is accepted because it raises the proxy alone.

- **Target:** the skill's `SKILL.md` and its reference files. **Off-limits:** cases,
  grader, runner and hidden checks (recorded as `harness_paths` and hash-gated).
- **Split:** fixed once, at random, stratified by family (`init --seed`), and stored in
  `_state.json`. The analyzer may read train transcripts and train rows only. Test
  rows' `explanation` fields name fact and claim ids, so they must not reach the
  analyzer. Test picks the winning round and is the headline.
- **Reps:** at least 3 per case (`init --reps`, which `run` uses by default). Reps of
  one case are correlated, so the runner's interval treats the case as the unit. With
  20 cases the whole-set noise floor is roughly +/-20 points, and wider on the 8-case
  test slice. More reps narrow per-case uncertainty but cannot add cases. Treat early
  rounds as **directional** until the set grows (#21).
- **Guardrails:** `bad_claims`, `noise_lines` and `behavior` must not regress outside
  noise. Report token usage and cost per case in absolute numbers before percentages.
- **Acceptance:** a candidate that wins on test must also hold up on the downstream
  confirmation tier before it is treated as an improvement.
- **Layout:** `.claude/hillclimb/comment-edit/` with `baseline/`, `v1/`, ... in the
  format the guides' report builder reads (`results.jsonl`, `traces/`, `errors.jsonl`,
  `summary.json`, `_state.json`).

## Sign-offs still required from the user

1. **Inputs.** Read the seed cases (`python -m evaluation.skill_eval.run cases`
   prints them; add `--with-ledger` to see the grader's facts, claims and
   references) and confirm they represent the edits the skill must handle, and
   what is missing. They were synthesized by an agent, the lowest-fidelity source
   in the build-eval guide. Real examples from your own projects should replace or
   anchor them.
2. **Grading.** After the first live pilot, open graded transcripts and say whether
   you would have scored any case differently. If so, the grader is not ready.
3. **Spend.** Live runs stay blocked until the smoke-run budget in #6 is set. The
   first paid run must quote cases x reps x model and a cost measured from a pilot.

## Running it

```text
python -m evaluation.skill_eval.run cases                 # list the seed cases
python -m evaluation.skill_eval.run selftest              # oracle/null/degenerate checks
python -m evaluation.skill_eval.run init --flow-dir <dir> --seed 7
python -m evaluation.skill_eval.run run --flow-dir <dir> --adapter oracle --variant baseline
```

Live runs: `run --adapter live --skill <variant> --model <id>` uses
`evaluation/skill_eval/live.py` (headless Claude Code, which spends money). Analysis:
`python -m evaluation.skill_eval.compare <flow> --split train` gives paired
comparisons against the control. After a grader or case fix, use
`python -m evaluation.skill_eval.regrade <flow> --reason "..."`. It rebuilds each end
state from its trace diff into a separate `<flow>-regraded` directory, with no model
calls, and must be disclosed as post-hoc.

`run` refuses to start until the harness files are approved for that flow
directory (`--approve-harness`, which records a hash). That approval belongs to
the user, because later unattended rounds run under it. The gate detects changes
and is not enforcement: any caller can pass the flag or edit `_state.json`.

A variant directory holds one adapter's rows. Resume skips completed
(case, rep) pairs, drops a truncated final row, and refuses to mix adapters.
Attempts that fail in the harness go to `errors.jsonl` with a failure class and
are never scored as model failures.

Hidden checks execute candidate code in a separate `python -I` process with a
timeout. That limits accidental interference, but it is **not** a security
sandbox. Live agent runs need the isolation from #7.
