# Domain docs

## Layout and reading rules

This repo uses a **single-context** layout:

- [Root intent](../../intent.md) records the user's product goals.
- [Architecture overview](../../architecture.md) records current structure and
  the status of proposed boundaries.
- `GLOSSARY.md` at the repo root contains domain terms.
- `docs/adr/` contains architecture decision records.

Before exploring the codebase, read the glossary and any ADRs relevant to the
area being investigated. If these files do not exist, proceed silently.
`domain-modeling` creates them lazily as terms or decisions are resolved;
empty placeholders are unnecessary.

If the repo later introduces a root `GLOSSARY-MAP.md`, follow its pointers to the
relevant context glossaries and check `src/<context>/docs/adr/` as well as the
root ADR directory.

## Use the glossary's vocabulary

Use canonical domain terms in issue titles, explanations, hypotheses, test names,
and code. When a needed term is missing, reconsider whether it belongs to the
domain or note the gap for `domain-modeling`.

Keep the glossary about domain language; implementation decisions belong in ADRs
when they warrant a durable explanation.

## Flag ADR conflicts

If a proposed change contradicts an existing ADR, identify the conflict and the
reason to revisit the decision explicitly, rather than silently overriding it.
