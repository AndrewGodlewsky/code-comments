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
