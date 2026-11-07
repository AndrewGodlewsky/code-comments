# Code Comments: behaviour spec and variant matrix

Status: proposed design (#24). It is built from the [principles ledger](principles.md).
Round 1 verdicts on these hypotheses are in [tournament-2026-11-07.md](tournament-2026-11-07.md).
The result was null against the control, so the hypotheses remain open.

## Behaviour spec (every variant)

The skill applies whenever a coding agent changes, fixes, refactors or reviews
source code, and when the user asks for a comment-only refresh. The 25 **core**
ledger principles apply in every variant. They group into five duties:

| Duty | What the agent does | Core principles |
| --- | --- | --- |
| **Keep it true** | Before finishing, find every comment, docstring and cross-reference the change falsifies (including outside the edited lines) and correct or remove it. Check each clause of comments near changed code. Keep comments attached to the code they describe. Never disarm wrong text with a label. | P-01, P-03, P-04, P-14, P-21, P-29 |
| **Capture what the code cannot say** | Record the non-obvious knowledge the evidence provides (constraints, invariants, couplings, deliberate oddities, the decisive choice that rules out a natural wrong alternative, a reason found for odd-looking code) in the scope it governs. Be specific, and write for a reader without the session. | P-05, P-06, P-07, P-08, P-18, P-19, P-20, P-22, P-23, P-24, P-27 |
| **Never invent** | Write a reason, history or contract only when evidence in hand supports it. Take an intended contract from evidence of intent, not from the code being fixed. Never invent an issue id. | P-02, P-07, P-16 |
| **Restraint** | Do not restate code, names or types. Do not comment for volume. Give each fact one home. Leave valid comments word for word. Never add commented-out code. In tests, let names explain. | P-09, P-10, P-13, P-16, P-26, P-32 |
| **Fit in** | Match the local comment form and vocabulary. | P-31 |

**Invariants that no variant may relax:**
- A comment-only request changes no code. Keep code identical, apart from comments and docstrings.
- Protected text survives: license headers, tool directives (`noqa`, `type: ignore`, pragmas), and still-valid rationale.
- No fabricated rationale, history, issue ids or contracts.

**Activation:** every variant uses the **same** frontmatter `description`, so the
tournament measures what the skill makes the agent do, not whether it triggers.
Trigger tuning is #20, run after a winner exists (skill-creator's description
optimizer).

## Variant matrix

The ledger has 10 variant axes. A full factorial design is impossible on 20 cases with
a noise floor near +/-20 points. Instead, there are two families of comparison:

- **Form** (four variants, identical axis positions): does the same content work
  better short, explained, as a procedure, or with examples? The "reference"
  positions are the ones most consistent with the core: CONTENT gap-driven,
  DENSITY sparse, CODE-FIRST family-aware, UNVERIFIED report, COMMENTED-OUT flag,
  STALE correct rationale and delete restatement, REJECTED-ALT plausible-only,
  API-DOCS non-obvious only, REPEAT owner only, PLACEMENT inline.
- **Stance** (one variant, same form as `principled`): flips the axes the ledger
  predicts move the two-sided trade-off most (CONTENT, DENSITY, REJECTED-ALT,
  REPEAT), towards writing more for a weaker reader.

| id | Varies | Hypothesis (falsifiable on `comment-edit` unless noted) |
| --- | --- | --- |
| `control` | No skill installed | Baseline: what the agent does unaided |
| `lean` | Form: about 60 lines, the duties stated with no explanation | Modern agents need only the essentials. Matches `principled` on `pass` within noise, at fewer tokens. Refuted if `principled` beats it beyond noise |
| `principled` | Form: every core principle with its reason (the skill-creator style: explain why, avoid rigid MUSTs) | Explaining *why* improves judgement. Beats `control` on `pass`, especially `maintain`/`audit` `bad_claims` |
| `procedural` | Form: the same content as an edit-time workflow (read comments as claims, then capture evidence, then a pre-finish diff scan) | An explicit final scan of the diff raises `maintain`/`audit` pass rates over `principled`. Refuted if it adds `noise_lines` without a `bad_claims` gain |
| `examples` | Form: `principled` plus a references file of contrasting good and bad comments from the sources | Concrete contrasts calibrate restraint and specificity, giving lower `noise_lines` on `restrain` and higher `recall` on `capture` than `principled` |
| `newcomer` | Stance: CONTENT why plus decisive what/how, DENSITY newcomer, REJECTED-ALT inline, REPEAT pointer | Writing for a weaker reader raises `capture` recall but fails `restrain` budgets more often. The proxy shows the cost; the benefit (if any) needs #19 |

**Known weak contrast:** `principled` already says to point to a fact's home rather
than copy it. So `newcomer`'s REPEAT position differs only in adding call-site
pointers on its own initiative. Expect little measured difference on that axis.

The axes that are deliberately **not** varied in this round, each with its reason:
- PLACEMENT belongs to #9.
- COMMENTED-OUT and API-DOCS have no case that plants their signal; add those cases in #21 first.
- UNVERIFIED's positions score the same on the proxy.
- CODE-FIRST (code-first) would mostly measure audit AST failures, which the invariant already forbids.

These axes are candidates for the climb (#27) once the eval can see them.

### Optional external comparator
*Keep the Why* (see `related-systems-and-researchers.md`) records rationale in
repository Markdown rather than inline. Adding it as an extra arm would show what
an existing skill does on this proxy. The proxy scores inline comments only, so it
would lose by construction. It belongs in the downstream confirmation (#19), and
only after its licence is checked.

## How the tournament picks a winner (#26)

> **Rescoped 2026-11-07.** This rule was applied in round 1 to the `comment-edit`
> proxy, and the result was null. The same rule (train selection, paired against a
> control, guardrails) now applies to the **downstream** score (#19). On
> `comment-edit`, a variant only has to pass the guardrails.

1. Run all six arms with the same model, harness, budget and split, at 3 or more reps.
2. **Screen on train.** Drop an arm whose train `pass` is not above `control`
   beyond noise, or that regresses `behavior`, `bad_claims` or `noise_lines`
   beyond noise.
3. Among survivors, prefer the higher train `pass`. **Break ties within noise by
   fewer skill tokens.** A shorter skill that is not measurably worse is the better
   default.
4. Report test-split results as confirmation only. Choosing on test among six arms
   would overfit 8 test cases.
5. Report per-family results for every arm. A null tournament (no arm beats
   `control` beyond noise) is a valid result and goes to the user before any climb.

## Overfitting controls

- The cases live in this repository. Variants were written from the ledger without
  reading case files, and `scripts/lint_skills.py` rejects any 8-word overlap with
  case text.
- Selection uses train. Test confirms, and #21's growth adds unseen cases before
  any claim.
- The proxy can be gamed (anchor stuffing, deletion). Guardrail metrics and the
  downstream confirmation (#19) are the defence.
