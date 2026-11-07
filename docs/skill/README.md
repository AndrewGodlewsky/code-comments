# Building the Code Comments skill

Status: steps 1-4 done offline (2026-11-07). Four distillation files hold 89
candidates with 369 verified citations. The ledger merges them into 33 principles
(25 core, 8 on variant axes) with 489 verified citations across the five files.
The design defines five variants plus a control, and all pass the linter.

**Pilot (user-approved, 2026-11-07):** 3 cases x 6 arms x 1 rep on
`claude-sonnet-5-5`, through the live adapter (`evaluation/skill_eval/live.py`).
- Results: the control passed 2 of 3; every variant passed 3 of 3. That is one rep
  on three cases, which is an anecdote, not evidence.
- Spend: $0.57 in total, against a projected ~$12 for the full Sonnet tournament.
- The wiring and isolation checks passed.
- On these cases the control was already at the ceiling for `maintain` and
  `restrain`, so a full tournament needs harder cases or a weaker model to have
  headroom (#26, #21).

**Tournament round 1 (2026-11-07):** 720 attempts on Sonnet 5.5 and Haiku 5.5, for
$13.60. It was a **null result**: no variant beats the no-skill control beyond noise.
On Haiku, the skills raise `capture` but rewrite still-valid comments in audits.
See [tournament-2026-11-07.md](tournament-2026-11-07.md).

**Rescope (2026-11-07, agreed with the user).** Round 1 measured the comment *writer*,
not the goal. The Haiku arms were wrongly framed as testing weaker models; there,
Haiku was the writer. The product goal is a later, possibly weaker, *reader* making
correct changes. Since then:
- the primary score is the downstream sequence eval (#19);
- `comment-edit` is a guardrail;
- no climb happens on the proxy.

See the fuller theory in `intent.md`.

**Decision (user, 2026-11-07):** build and compare skill variants now, in parallel
with the placement pilot (#9), instead of waiting for it. This changes the order of
work, not the evidence bar. No claim that a variant improves agent outcomes, or
that inline comments beat documents, is made until the evals and #9 support it.

## Pipeline: from sources to a tested skill

| Step | Output | Issue |
| --- | --- | --- |
| 1. **Map.** Per-source-group extraction of candidate principles, with verbatim quotes tied to passage ids, evidence type and opposing views | `distillation/<group>.md` | Ledger issue |
| 2. **Reduce.** Merge into one traceable ledger. Each principle records citations, evidence strength, conflicts, the eval metric that would detect it, and its disposition: core, variant axis, or rejected | `principles.md` | Ledger issue |
| 3. **Spec.** Behaviour spec for the skill and a variant matrix with one hypothesis per variant | `design.md` | Spec issue |
| 4. **Variants.** Each variant is a complete, installable `code-comments/` directory built only from ledger principles, plus a linter for format, portability and traceability | `../../skill-variants/` | Variants issue |
| 5. **Guardrail screen.** Every variant runs on `comment-edit`; variants that invent reasons, leave false comments or rewrite valid ones are fixed or dropped (round 1 done) | flow under `.claude/hillclimb/` | #26 |
| 6. **Downstream tournament and climb.** Compare surviving variants against an AI-maintained docs folder and no added context, on a weaker reader's follow-up changes across sequences; climb the winner on that score; promote it | `skills/code-comments/` | #19, #27 |

Steps 1-4 are offline. Steps 5-6 need the live agent adapter (#18) and a run
budget (#6).

## Rules that keep the distillation honest

- **Traceability.** Every principle cites passage ids that exist and quotes that
  appear verbatim; `scripts/check_distillation.py` verifies both. Every variant
  lists the principle ids it encodes, and the linter checks that they exist.
- **Conflicts become experiments.** Where sources disagree (for example, how much
  to comment, or whether code should explain itself), the disagreement is a variant
  axis, not an editorial choice.
- **Evidence strength is explicit.** Empirical findings on LLMs outrank expert
  opinion about agent behaviour. Historical practice is a hypothesis about what
  transfers, not a rule.
- **Variants come from the ledger, not the cases.** The eval cases are visible in
  this repository. A variant tuned to their wording would win the tournament without
  being better. Variant text must not paraphrase case material. Overfitting is
  checked by the train/test split and later by the case growth in #21.

## Variant layout

```text
skill-variants/
  variants.json                 # id, hypothesis, axis values, principle ids
  <variant-id>/code-comments/   # installable as-is: name must equal the directory
    SKILL.md
    references/...              # only if the variant uses progressive disclosure
```

The eventual winner is promoted to `skills/code-comments/`, the portable path that
`gh skill install` discovers (see [skill portability](../research/skill-portability.md)).
