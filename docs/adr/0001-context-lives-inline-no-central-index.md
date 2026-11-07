# ADR 0001: Context lives inline beside the code; no central index

- **Status:** accepted (user decision, 2026-11-07)
- **Deciders:** the user
- **Related:** `intent.md` ("Scope clarification"), [trade-off analysis](../skill/inline-only-tradeoffs.md), #19, #33

## Context

The Code Comments skill exists to remove a second source of truth: an AI-generated
`docs/` folder that describes the code and drifts away from it. Two findings made a
**central index** look attractive:
- an always-loaded index improved agent discovery in one vendor test
  ([R1](../research/docs-for-agents-practice.md));
- separate documents drift ([R3](../research/human-maintenance-and-drift.md)).

The proposal was a short `docs/` index generated from the comments, so agents
would get an up-front map while comments remained the only maintained content.

## Decision

The skill keeps context **only in comments, as close as possible to the code they
describe**. It creates and maintains **no central index, generated docs view, memory
store, or lookup service**. Agents find context in two ways:
- **Point of edit:** a file must be opened to be changed, so its comments are seen
  exactly when they matter.
- **Search:** context elsewhere is plain text beside the code it describes, so
  `grep` or `ripgrep` can find it.

## Why

1. **The code is the source of truth.** It is what runs. Every artefact that
   restates it is a second source that can disagree with it.
2. **Human editors.** The skill must also let a person change the code by hand. A
   person editing code will not know that an index exists, or how to regenerate it.
   If regenerating it needs an AI run, forgetting to do it puts the project back out
   of sync, which is the exact failure this project exists to remove.
3. **Closeness reduces drift.** A comment beside the changed lines appears in the same
   diff and the same review. Separate documents and indexes do not. R3 found that
   comments change together with code far more often than separate documentation does.
4. **Simplicity.** An index adds a format, a generator, a freshness check, and a new
   way to be wrong. The skill should need nothing beyond the source files.

## Alternatives rejected

| Alternative | Why rejected |
| --- | --- |
| AI-maintained `docs/` folder (the user's prior practice) | The two-sources-of-truth drift this project exists to remove. It remains the *comparator* in #19, not a design option |
| Index generated from comments | Still a second artefact. It needs regeneration after manual edits that humans won't run, and it complicates the skill |
| Memory system owned by the skill | Decision memory is a separate layer the user maintains elsewhere; the skill must not take control of it (`intent.md`) |

## Consequences

- Cross-module knowledge must be written where it will be **encountered**. That means
  at the owner, plus a short pointer at dependent sites (AXIS-REPEAT, position b),
  because nothing central will surface it.
- Discovery quality depends on comments being searchable. A possible future aid is a
  consistent tag or syntax convention for `grep` and `ripgrep` (#34). It would be
  written in the comments themselves, not in a separate index.
- Mechanical checks that read the code itself remain compatible with this decision.
  An example is a CI lint that flags comments naming identifiers that no longer
  exist: it maintains no second source.

## Revisit if

#19 shows that readers systematically miss context living in **other** files (the
agent never opens or searches the file that holds the fact), and pointer comments
and search conventions do not fix it. Any reconsideration must still meet reason 2:
nothing that a human editing code by hand can leave out of sync.
