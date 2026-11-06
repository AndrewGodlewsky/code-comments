# Offline Fixture Implementation Plan

> For agentic workers: implement this bounded plan locally with test-first checks
> and a fresh independent whole-branch review, following the repository's task
> tracking and closeout workflow. The user requested planning and starting work;
> routine implementation decisions do not require another permission round.

**Goal:** Make the first experiment boundary executable without model spending.

**Architecture:** One original fixture and a small offline audit/export module.
Evaluator assets stay outside exported inputs. This is not the isolated runner.

**Tech Stack:** Python 3.12+ standard library, JSON, unittest.

**Spec:** [Offline fixture design](../specs/2026-11-05-offline-fixture-design.md).

## Global constraints

- No network or model calls; no new dependencies.
- Export only the first task and currently available facts.
- Refuse existing destinations; do not delete or overwrite user work.
- Keep published toy solutions out of eventual held-out datasets.
- Issue #5 owns this branch; #4 and #6–#12 remain open after its closeout.

## Review focus

- Future information leaks: enumerate export paths and inspect content.
- Unequal facts: compare both placements with literal initial facts and exclude
  future facts, while checking baseline behavior is identical.
- Obsolete facts: reject the old maximum after step 2 without losing zero/default.
- Incorrect grader: reject mutants and runtime/syntax failures, accept all oracles.
- Data loss: existing destinations and invalid conditions must leave files intact.

## Task 1: fixture and independent checker

Files: `evaluation/fixtures/retry-policy/manifest.json`, `initial/policy.py`,
`private/checks.py`, `private/step-{1,2,3}.md`, `private/reference/step-{1,2,3}.py`;
`tests/test_offline.py`.

- [x] Write tests for the audit and checker contract, observe missing behavior.
- [x] Implement hand-derived step assertions and original reference checkpoints.
- [x] Check default, zero, explicit override, invalid types/ranges, the new upper
  bound and literal retry schedules. Check incorrect implementations are rejected.

## Task 2: export and local audit

Files: `evaluation/__init__.py`, `evaluation/offline.py`, `tests/test_offline.py`.

Interfaces: `export_workspace(destination: Path, condition: str) -> None`;
`audit() -> dict`; evaluator `check(source: str, step: int) -> list[str]` returns
failure descriptions. CLI accepts `audit` or `export` with the arguments in spec.

- [x] Write failing export tests for the three conditions, overwrite and invalid
  condition cases; assert actual exported behavior and no private/future assets.
- [x] Implement allowlisted export and JSON audit. Keep known-good and mutant
  outcomes distinct; report zero model calls, not an efficacy score.
- [x] Run the complete unittest suite and both CLI paths on temporary directories.
- [x] Commit/push the verified implementation checkpoint with issue evidence.

## Task 3: documentation and closeout

Files: `README.md`, `architecture.md`, `docs/research/README.md`,
`docs/evaluation/README.md`, `.gitignore`; roadmap already owns portfolio links.

- [x] Reconcile current implementation claims and tested commands; document
  visibility limits, provenance and next issues. Ignore Python bytecode.
- [x] Run all tests on installed Python 3.12 and default Python, check Markdown
  links/whitespace, review/stage only task files and push the final checkpoint.
- Closeout remains tracked in #5: obtain independent review against exact head/base, integrate main,
  remove only this task branch, obtain final audit and close only #5.

Execution evidence and any rulings belong in #5 comments, not a duplicate task
status document. Update these checkboxes at the final checkpoint; GitHub owns
post-integration status. No approved budget means paid work remains pending #6.
