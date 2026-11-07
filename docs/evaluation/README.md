# Offline evaluation foundation

This is the first executable step of the [product roadmap](../roadmap.md), tracked
in [#5](https://github.com/AndrewGodlewsky/code-comments/issues/5). The user chose
offline work only. There are no model calls, credentials, API adapters or new
package dependencies. These checks are not benchmark results for a model or skill.

For the separate #8 corpus work, see the [admission audit](corpus-audit.md) and
[Hashin executable preflight](hashin-preflight.md). The latter has optional Docker
and host PyArrow prerequisites; it does not change this fixture's requirements.

## Run locally

From the repository root, use Python 3.12 or newer:

```text
python -m unittest discover -s tests -v
python -m evaluation.offline audit
python -m evaluation.offline export --condition inline --destination <new-directory>
```

Replace `<new-directory>` with a path that does not exist. Conditions are
`baseline`, `inline`, and `external`. Even an existing empty directory is refused;
choose a fresh destination instead of deleting someone else's work. An export
contains `policy.py`, `TASK.md`, `README.md`, and `context.md` only for the external
condition. All exports start at the first edit. There is no trajectory executor
or continuation command yet.

The audit writes JSON to stdout, returns zero on success and nonzero on failure.
It checks four known-good states (initial plus three edits) and rejects five
specific incorrect variants. Report fields distinguish reference acceptance from
mutant rejection and explicitly record `model_calls: 0`. The active fact IDs show
when the five-retry limit is replaced and when the delay requirement becomes known.
Redirect stdout if a report file is useful; tests use temporary directories and
leave no exported workspaces in this repository.

## What the fixture establishes

[retry-policy](../../evaluation/fixtures/retry-policy/manifest.json) is an original,
public development diagnostic. It exercises None-versus-zero semantics, override
precedence, a deliberately superseded upper bound, and cumulative delay behavior.
The checker uses hand-derived expected values independently of the references.
Inline and external conditions receive the same current fact strings. Code and
ordinary task instructions remain equivalent across all three conditions.

The source, requirements, fact ledger and reference solutions are authored here;
no third-party benchmark code was copied. The project has not selected a
distribution license. A public fixture is already exposed and must not later be
presented as an uncontaminated held-out sample. Much of its context is recoverable
from code/tasks; it diagnoses plumbing, not the need for historical rationale.

## Boundaries still required

The audit executes trusted checked-in Python directly in its own process. It is
not safe containment for arbitrary or adversarial code and does not claim to
detect every incorrect implementation. It has no candidate-code input option.
The `private/` directory is evaluator-owned but public in Git. The exporter uses
an allowlist to avoid copying answers, future tasks, facts and graders; that
alone does not stop an agent from reading neighboring paths or the internet.

Before model execution, [#7](https://github.com/AndrewGodlewsky/code-comments/issues/7)
must supply real isolation, resource limits, session resets, persisted trajectories,
independent grading and trace/cost records. [#8](https://github.com/AndrewGodlewsky/code-comments/issues/8)
owns representative corpus selection and review. [#6](https://github.com/AndrewGodlewsky/code-comments/issues/6)
remains pending under the user's offline-only direction. The
[evaluation protocol](../research/evaluation-protocol.md) still owns study design;
none of its example budgets, sample sizes or efficacy margins is adopted here.
