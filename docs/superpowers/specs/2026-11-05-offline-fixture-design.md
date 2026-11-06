# Offline fixture foundation

Scope: [#5](https://github.com/AndrewGodlewsky/code-comments/issues/5), first child of
the [product roadmap](../../roadmap.md). The user asked us to plan remaining work
and start it. This bounded foundation needs no paid model selection. Product
workflow and benchmark claims remain open under the canonical protocol.

## Deliverable and engineering choices

Use Python 3.12+ standard library, available locally, with `unittest`. No packages,
network calls, model adapters, general runner framework, or installer in this slice.
Implement the small shared contract locally; a separate agent reviews the design
and completed branch. These are coordinator choices, not previously user-selected
languages or evidence-backed product decisions.

One original synthetic fixture concerns retry policy. Its initial function
`resolve_retries(settings)` uses three retries for missing/None values, preserves
explicit zero, accepts only actual integers in 0..5, and raises ValueError for
other values (including bool). Retries exclude the initial operation. Three edits:

1. Add `override=None`, with any non-None override taking precedence; keep zero.
2. A documented backend upgrade changes the maximum from five to eight; all
   other semantics remain. The old cap must now be retired.
3. Add `retry_delays(settings, override=None)` returning one delay per retry:
   1, 2, 4, 4, ... seconds. Do not add a delay for the initial operation.

Evaluator assertions are hand-derived from these contracts. All checkpoints must
pass still-valid behavior. Mutation controls must reject a zero/default confusion,
a stale cap, a lost previous constraint and an extra initial-operation delay.
No actual external product history is claimed: provenance is the authored fixture
contract. The public development fixture will never be a held-out confirmation set.

## Data and visibility

`evaluation/fixtures/retry-policy/manifest.json` owns fixture identity, factual text,
introduction/retirement steps and provenance. `initial/policy.py` holds the initial
implementation. `private/` contains later requests, reference checkpoints and the
independent behavioral checker. Private means evaluator-owned in this repo; it
does not claim secrecy from a local process or from the internet.

Export only the first-step task, initial implementation, and common reading guide
to a newly created destination. Conditions: `baseline`, `inline`, `external`.
Inline and external exports use identical currently valid fact strings; only
their placement changes. Inline facts sit directly above the function. Baseline
has no added fact inventory. External context lives in `context.md` with an owning
function heading. The guide points to source and context.md if present in every
arm. Future facts, later requests, manifest, graders, reference solutions and Git
metadata are never copied. Refuse any existing destination, even if empty, and
reject invalid conditions before writing. These exports are **not** an OS sandbox;
#7 must isolate agent execution before experiments.

## Execution and tests

`python -m evaluation.offline audit` emits JSON and exits zero only if the initial
implementation and all reference steps pass and every diagnostic mutant is
rejected. The report explicitly says offline fixture audit and zero model calls.
The audit executes only trusted checked-in fixture code. Do not expose a command
for arbitrary model patches or imply adversarial containment.

`python -m evaluation.offline export --condition inline --destination <new-path>`
exports the first task. It does not advance a trajectory or grade an agent.
`python -m unittest discover -s tests -v` checks export boundaries, literal fact
equivalence, overwrite refusal, unchanged initial behavior, complete audit results,
and checker rejection of known incorrect programs. Syntax/runtime failures must
produce failed checks, not success or a misleading partial pass.

No model performance, statistical significance, billing, broader source-code
compatibility or four-client portability is established by these checks.
