# Roadmap: a comment hygiene plugin for Claude Code

[Parent issue #4](https://github.com/AndrewGodlewsky/code-comments/issues/4) owns the
remaining intent, and child issues own their own branches. GitHub is the live source
for status and assignment. This page records the direction and the order of the work,
not a second checklist.

## How the goal changed

The project set out to show that well-kept inline comments help a later, possibly
weaker, model make better changes. The
[long-horizon pilot](evaluation/pilot-report-2026-11-08.md) (#37) found no measurable
benefit. On six real pull requests, the full skill did no better than one general
"keep the codebase clean" sentence.

The product was therefore narrowed (2026-11-08) to **comment hygiene**: keep comments
true, record reasons the code cannot show, never invent a reason, and add no noise.
It makes no performance claim. The [purpose document](skill/hygiene-skill.md) sets out
what the skill does and does not do.

## Done

| Work | Issue | Evidence |
| --- | --- | --- |
| Long-horizon pilot: no downstream benefit | [#37](https://github.com/AndrewGodlewsky/code-comments/issues/37) | [Pilot report](evaluation/pilot-report-2026-11-08.md) |
| Hygiene skill shipped as a Claude Code plugin | [#45](https://github.com/AndrewGodlewsky/code-comments/issues/45) | [Plugin](../plugins/code-comments/README.md), [hygiene eval](../evaluation/hygiene/README.md) |
| Iteration 5: the skill against a one-line reminder | [#46](https://github.com/AndrewGodlewsky/code-comments/issues/46) | [Hygiene eval](../evaluation/hygiene/README.md), [purpose document](skill/hygiene-skill.md) |

## Next

| Work | Issue | What finishes it |
| --- | --- | --- |
| Does the skill load on its own? | [#20](https://github.com/AndrewGodlewsky/code-comments/issues/20) | Recall on code-editing requests and specificity on other requests, measured with `claude plugin eval` on Haiku and Sonnet |
| A second case per behaviour, plus TypeScript | [#21](https://github.com/AndrewGodlewsky/code-comments/issues/21) | Twelve new graded cases run in the three iteration-5 arms, with results reported next to iteration 5 |
| A clean install in Claude Code | [#12](https://github.com/AndrewGodlewsky/code-comments/issues/12) | The user installs, uses, disables and removes the plugin in a fresh session. A license and version scheme are chosen before any wider announcement |
| Four candidate skills incubated; none reliably beats its one-line reminder, and none ships | [#50](https://github.com/AndrewGodlewsky/code-comments/issues/50) | A separate agent's review, verified integration into remote `main`, issue reconciliation, branch and worktree cleanup, and an independent final audit ([git workflow](agents/git-workflow.md)); the closeout agent then moves this row to Done. Evidence: [Incubator](../incubator/README.md), [planning-research overview](planning-research-2026-11-11.html) |

## Options after the incubator results (#50)

These are options for the user, not decisions. Nothing in the incubator moves into a
plugin unless the user decides it should. The
[planning-research overview](planning-research-2026-11-11.html) has the evidence and the
open questions.

- **Keep all four in the incubator, and stop.** None reliably beat its reminder sentence
  on graded checks, on either model, in training or on the held-out pair. Accepting that is also a
  choice.
- **Adopt one or more reminder sentences.** Each skill's `eval/arms.json` holds its
  sentence.
  - Where a sentence would live is untested. It could go in the request (the only place
    tested), in the user's `CLAUDE.md` or `AGENTS.md`, or in the shipped `SKILL.md`.
  - constraint-sweep's sentence showed no gain over the bare model.
- **Raise the shipped-skill finding on #21 and #48.**
  - When read, the shipped skill was the only arm to fail hidden tests: 111 of 120 runs
    passed, against 120 of 120 in every other arm. Six failing runs broke a constraint
    stated elsewhere, and three built only part of the requested change. Each noticed the
    constraint or error first.
  - The comparison was chosen after reading the runs. Its cause, the shipped skill's
    "make the change if asked and tell the user" conflict rule or its ask-first guidance,
    is a hypothesis. A targeted eval would test it before anyone rewords those lines.
- **Fold parts of change-drift-sweep into the shipped skill (#21, #48).** The parts are
  its list of old forms, its derived-figures rule and its record rule. Its rule set
  before the runs makes it a plugin enhancement, since the shipped skill tied it. Adding
  them would wait for a case where the shipped skill misses such a value, and would need
  a no-harm check.
- **Decide whether retiring a docs page is still in scope** after the 2026-11-09 narrowing.
  - fold-docs-inline has a clear lead over the shipped skill and the bare model in
    training (full-mark runs 23/25 against 4/25 and 1/25). On its held-out pair it leads
    both on checks (96/100 against 82/100 and 79/100). At run level only its full-marks
    lead over the bare model holds (8/10 against 1/10, stratified exact p = 0.007; full
    core 8/10 against 7/10). Its held-out lead over the shipped skill is not established
    (full marks 8/10 against 4/10, p = 0.14; the shipped skill had 1/10, p = 0.007, before
    three auditor rulings on its runs).
  - Its lead over the reminder (89/100) is not established.
- **Fix the graders and the harness offline.** These need no model runs, and the
  planning analyses put them before any paid run:
  - the grader gaps each README lists, then a re-grade of every counted iteration;
  - harness changes: a second, named reminder arm (fold-docs-inline's
    [next step 3](../incubator/fold-docs-inline/README.md#next-steps)); an arm that loads a
    candidate together with `code-comments` (the incubator's
    [limits](../incubator/README.md#limits-shared-by-every-eval-here)); guard-safe run
    prompts (the incubator's [guard note](../incubator/README.md#running-an-eval) and
    change-drift-sweep's [next step 4](../incubator/change-drift-sweep/README.md#next-steps));
    and run-level full-core counts (the
    [research index lessons](research/README.md#incubator-evaluations-and-their-lessons-50)).
- **Paid follow-ups.** Each needs the user's approval and a cost cap. Run counts are
  planning estimates:
  - A: replicate the shipped-skill harm, 30 Haiku runs at stage 1;
  - B: fold-docs-inline against a stronger reminder, 60 to 90 runs;
  - C: constraint-sweep's named form, 20 to 40 runs;
  - D: a no-harm check before folding change-drift-sweep into the shipped skill, 80 runs;
  - E: a large-repository case family, gated on the reminder as well as the bare model,
    about 68 runs to its stop-or-go point;
  - F: verify-before-relying's `python -B` line, about 20 runs.

#50's own runs were approved in the user's request of 2026-11-11, which asked to
"research, test, implement, and eval all of your ideas as separate skills" and said "it is
totally fine if Opus runs until it hits its usage limit, ensuring rigorous testing on
everything and evals and everything". The cap was the plan's usage limit: no dollar or
per-run cap was set and no cost estimate was made before the runs. The runs were
in-session workflow subagents, not headless `live.py` runs. Their measured token usage is
in the [incubator README](../incubator/README.md#cost-of-50); no billed cost is recorded.

## Parked

- **Orca, Codex and GitHub Copilot distribution.** Parked until there is a reason to
  support another client (#12).
- **Comment tag conventions for grep** (#34). Later research.
- **Longitudinal runner and corpus** (#7, #8). Other agents' branches. The hygiene goal
  does not need them.

## Rules

- **Publish null and negative findings,** and narrow the claims to fit them. A
  positive result is not something to manufacture.
- **Paid runs need the user's approval** and a cost cap. Report the estimated and the
  actual cost.
- **Score preservation and restraint alongside capture.** A change that raises one at
  the cost of another is not an improvement.
- The [evaluation protocol](research/evaluation-protocol.md) remains the record of the
  original experimental design. Its performance questions are answered for now by the
  pilot.
- The parent issue closes when its completion criteria are met or the user agrees a
  revised outcome, not because the tickets ran out.
