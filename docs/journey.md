# How we got here: the Code Comments story

This document follows the thinking behind the project from its starting intuition to
now. Each step links to the evidence or result that drove it. Use it to explain the
project to someone, or to recover context in a new session. `intent.md` remains the
authoritative record of the user's goals.

## The 60-second version

> AI coding works better on big projects when the agent has documentation explaining
> the code, but a separate `docs/` folder becomes a second source of truth that drifts
> away from the code. Code Comments is a skill that keeps the *useful* part of that
> explanation inline, beside the code it describes, where agents and people read it
> and where it is more likely to stay true. We have researched what good explanation
> is, built an eval and five versions of the skill, and run 738 graded attempts. The
> skills reliably make agents record the *why* more often, but no version yet beats
> "no skill" overall, and we have not yet measured the real goal: whether a *later*,
> weaker agent does better because of those comments. That is the next experiment.

## 1. The starting intuition (user, 2026-11-04 and 2026-11-07)

From experience, in large and fast-changing codebases, AI coding needs three kinds of
context:
1. **Decision memory:** why decisions were made, and what was rejected.
2. **Instructions and intent:** repository guidance and the product's purpose.
3. **Documentation of what the code does.** Having the AI generate a `docs/` folder
   alongside the code made future changes less likely to go wrong, especially for
   weaker models, because it explains effects and relationships ("this affects that").

The problem with layer 3 is **two sources of truth**. Nobody knows which documents a
change affects, so the docs drift, and humans especially won't keep them updated. The
idea: keep that knowledge **inline, as comments**, maintained by a skill.
Frontier models may need it less; weaker models and human editors may need it more.

Recorded in [intent.md](../intent.md) ("The user's fuller theory").

## 2. Research first (2026-11-04 to 11-06)

The user asked for evidence before workflow decisions.
- **Historical and craft sources.** Thirteen books, papers and essays were extracted
  passage by passage, with traceable citations: von Neumann (1947), the 1956 FORTRAN
  manual, Knuth, Parnas, Fowler, Beck, *The Pragmatic Programmer*, *Software
  Engineering at Google*, Ousterhout, and four empirical LLM studies. See the
  [comment-context collection](research/comment-context/README.md) and the
  [historical review](research/historical-comment-design.md).
- **Empirical evidence and benchmarks.** See the [deep-dive summary](research/deep-dive-summary.md),
  [agent-context evidence](research/agent-context-evidence.md) and the
  [benchmark landscape](research/benchmark-landscape.md).
- **What it said.** Correct context can help models, and wrong or stale context
  reliably hurts them. No study had compared maintained inline comments with
  equivalent documents over successive changes. That gap is what this project tests.
  The canonical experiment design is the [evaluation protocol](research/evaluation-protocol.md).

## 3. An eval for the comment writer (2026-11-06)

**Built:** `comment-edit`, 20 small cases in four families: record the *why*, fix
stale comments, don't add clutter, and comment-only refresh. It has an automatic
grader and a self-test that proves the grader catches deliberately bad output.
See the [eval plan](evaluation/skill-evals.md).

**Why:** a skill can only help later agents if it writes accurate, useful comments
in the first place.

## 4. Turning research into a skill (2026-11-07)

- **Map and reduce.** Four parallel extractions produced 89 candidate principles,
  merged into a ledger of **33 principles**, each graded by evidence strength, with
  369 machine-verified quotes (489 citations across all five files). Only **2** are
  backed by consistent LLM evidence:
  - fix or remove comments your change makes false;
  - keep each comment attached to the code it describes.

  Where the sources disagreed (for example, the expert rule "comment *why*, not
  *what*" is not clearly supported for models), the ledger recorded the disagreement
  as a **variant axis** to test rather than deciding it. See the
  [principles ledger](skill/principles.md).
- **Five variants** test different forms: `lean`, `principled`, `procedural`,
  `examples` and `newcomer`. See the [design](skill/design.md) and
  [skill-variants/](../skill-variants/).

## 5. Running it (2026-11-07)

- An 18-attempt pilot ($0.57), then **720 graded attempts** ($13.60): five variants
  plus a no-skill control, 20 cases, 3 repetitions, on **Sonnet 5.5 and Haiku 5.5
  as writers**.
- **Result:** no variant beats the control beyond noise. Consistently, though, every
  skill raises "record the why" (0.60 → up to 0.93). A weaker writer with a skill
  sometimes rewrites still-valid comments. The skills cost 26-87% more per attempt.
- Reading the failures found grader mistakes, which were fixed, regraded and
  disclosed. Full detail is in the [eval report](evaluation/report-2026-11-07.md);
  the raw numbers are in [evaluation/runs/](evaluation/runs/).

## 6. The correction (2026-11-07)

Asked whether the evals reflect the goal, we found two mistakes:
1. The eval measures the comment **writer**, but the goal is a **later reader** making
   correct changes. We had begun treating the writer score as the target.
2. Haiku was described as testing "the weaker model of the hypothesis", but in the
   tournament Haiku was *writing* the comments, not reading them.

**What changed:**
- The writer eval became a **guardrail**.
- The primary experiment became **#19**: a capable writer maintains context over a
  sequence of changes (inline skill, AI-maintained docs folder, or nothing), and a
  fresh **weaker or frontier reader** makes the next change.

The tournament report and the issues carry the correction.

## 7. Testing the theory against outside evidence (2026-11-07)

| The user's claim | What the evidence says | Report |
| --- | --- | --- |
| Others find docs folders help AI on large projects | **Widely reported; weakly measured.** Teams build elaborate docs folders, but controlled studies of agent context files found no correctness gain | [docs-for-agents-practice.md](research/docs-for-agents-practice.md) (R1) |
| Separate docs drift (two sources of truth) | **Strongly supported.** 82% of top projects had stale doc references at some point. Agents followed a stale instruction file over the actual code 90% of the time. Only 37% of agent pull requests that changed code touched docs | R1; [human-maintenance-and-drift.md](research/human-maintenance-and-drift.md) (R3) |
| Weaker models need the context more | **Refined.** Benefit tracks whether the reader *lacks* the fact and *can use* it. The weakest models gain little, and frontier models gain a lot from knowledge the code doesn't contain | [capability-gradient.md](research/capability-gradient.md) (R2) |
| Humans struggle to edit AI code without comments | **Not supported yet.** The one controlled trial found no penalty. Comments raised confidence more than accuracy | R3 |
| Inline stays truer than a docs folder | **Partly.** Comments change with code far more often than docs, but still lag at callers and interfaces. Never compared over a sequence of changes: #19 | R3 |
| Where the skill should focus | **Local rationale, not description.** The knowledge least often written down is constraints and rejected alternatives; describing what the code does adds little for capable readers | [context-layers.md](research/context-layers.md) (R4) |

**The reframe:** the skill should replace the **useful part** of a docs folder (local
constraints, effects, and why), not re-describe the code. The skill's principles
already lean this way, and #19 now tests it directly.

These reports were written by research agents and have not yet had an independent
citation audit (#29).

## 8. Where it stands

- **Next experiment:** #19, the inline skill against an AI-maintained docs folder
  against nothing, judged by weaker and frontier readers over sequences of changes,
  with realistic drift. It starts on small cases, then moves to medium and large real
  codebases (#8), ideally including the user's own project.
- **Fix first:** the weaker-writer rewriting problem in the skill text, and one
  defective eval case.
- **Reports:** each eval run produces an auto-generated numbers report; each decision
  point gets a narrative report ([policy](evaluation/report-2026-11-07.md#7-do-we-write-a-report-every-time)).

## Document map

| To understand | Read |
| --- | --- |
| The user's goals and theory | [intent.md](../intent.md) |
| The research | [research/README.md](research/README.md) |
| What the evals measure and how runs went | [evaluation/report-2026-11-07.md](evaluation/report-2026-11-07.md) |
| The skill's principles and variants | [skill/principles.md](skill/principles.md), [skill/design.md](skill/design.md) |
| Tracking | GitHub issues: #4 (roadmap), #19 (primary experiment), #28 (skill), #29 (evidence) |
