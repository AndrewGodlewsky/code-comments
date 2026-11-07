# #19 stage-1 smoke run: findings (2026-11-07)

The numbers are in [runs/2026-11-07-seq-smoke.md](runs/2026-11-07-seq-smoke.md).
The design is described in [skill-evals.md](skill-evals.md) and issue #19. The user
approved a smoke run estimated at $1-2; it cost **$1.12**.

## What ran
- **Main run:** 10 two-step sequences (7 tagged non-derivable, 3 local-visible
  controls) × 3 arms (`code-only`, `docs-folder`, `inline:lean`) × 1 rep, with a
  Sonnet 5.5 writer and a fresh Haiku 5.5 reader. That is 30 attempts with 0 harness
  errors.
- **No-context control:** the correct step-1 code with **every comment and docstring
  stripped**, followed by the same Haiku reader. Ten attempts, about $0.02 in total.

## Result: nothing discriminates, and the control explains why

| Arm | Reader pass | Facts recorded (comments or docs) | Facts in comments | Reader opened docs | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| code-only | 10/10 | 0.90 | 0.90 | — | $0.28 |
| docs-folder | 10/10 | 1.00 | 0.75 | 10/10 | $0.49 |
| inline:lean | 10/10 | 1.00 | 1.00 | — | $0.32 |
| **no context at all** | **10/10** | 0.00 | 0.00 | — | $0.02 |

1. **A strong writer records the *why* without being asked.** Sonnet 5.5 with no
   skill put the required facts into comments in 9 of 10 sequences. So "code-only"
   was not a no-knowledge arm.
2. **The reader didn't need the knowledge at all.** With every comment removed, Haiku
   still passed all 10. In `seq-ledger-refund`, for example, it copied the
   deduplication pattern from the existing `apply()` method into the new `refund()`
   method. It never needed to know *why* refunds must be deduplicated, because the
   code already showed *how*.

**The sequences were mislabelled.** In small, self-contained modules, the behaviour a
follow-up needs is usually embodied in neighbouring code, and a capable reader copies
it. The authors checked that a *naive* implementation fails, but the reader isn't
naive: it follows existing patterns. The harness worked end to end:
- the hand-off removed the evidence;
- the docs arm wrote on average 3 docs and every reader opened them;
- the costs were measured.

## What this means for the hypothesis

It neither supports nor refutes the claim. Context could not matter here, because
the code already carried everything the reader needed. That fits the research:
- context helps when it carries **knowledge the code lacks** and the reader has
  headroom ([capability-gradient.md](../research/capability-gradient.md));
- the user's claim is about **large, cross-module** code, where the relevant pattern
  sits in a file the reader may never open ([inline-only-tradeoffs.md](../skill/inline-only-tradeoffs.md), C1).

Our sequences had neither property.

One real measurement: the docs-folder practice cost **73% more per sequence** than
code-only, while every reader opened the docs. The inline practice cost 13% more.

## Changes before any larger run
1. **An empirical derivability gate.** A sequence counts as non-derivable only if the
   **no-context control fails** for the target reader across several reps. This costs
   about $0.002 per attempt with Haiku. Labels assigned by authors are not enough.
2. **Genuinely non-derivable sequences.** The needed constraint must not be embodied
   in code the reader will see. Candidates:
   - new behaviour in a *different* module from the one that carries the pattern;
   - constraints about external systems with no existing code example;
   - follow-ups whose natural pattern-copy is the wrong answer.
3. **Bring real codebases forward (stage 2).** Cross-module effects in medium and large
   repositories are where the hypothesis lives, and where small synthetic modules
   can't reach. The container and vulnerability-scan gates apply.
4. **Harder readers or drift.** Add the D1/D2 drift steps, and consider a lower-effort
   reader setting as a weaker-reader tier within the same harness.
