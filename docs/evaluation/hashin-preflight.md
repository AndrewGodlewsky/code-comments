# Hashin executable admission preflight

**Hashin remains pending.** The 2026-11-06 offline probe reproduces all five
public reference states in one pinned image and catches two first-step mutants.
Frozen earlier assertions also fail against later states. This advances #8's
execution evidence; it does not admit a placement-pilot candidate.

## Selection, provenance and exclusions before results

The [registry](../../evaluation/corpus-candidates.json) selected this sequence on
2026-11-05, before execution. This follow-up chose Hashin for its small Python CLI,
available image and MIT repository declaration, before seeing test outcomes.
The other five candidates remain pending, not excluded for their outcomes.
This is one feasibility sequence, not a powered sample or cross-repository result.

Inputs are the same pinned [ChainSWE unique parquet](https://huggingface.co/datasets/C-lister/ChainSWE/resolve/dcaa484eca5b38caca71420712b1b194c1235d6e/data/unique.parquet),
row 1 (`peterbe_hashin_20180808_fa5563e40100136f`), and the image resolved from its
declared tag. The parquet SHA-256 is
`f7de0d66b64a9d5c28921fba2bbd51b5131dae8d5c789e03e61c09e67fc355fe`.
The script verifies those bytes before decoding with host PyArrow 24.0.0.
The [raw execution record](../../evaluation/evidence/hashin-preflight-2026-11-06.json)
includes each reference/test patch's SHA-256, the probe source hash, all commands,
exit codes, output and individual test results. Timing and temporary names vary.

The image is pinned to
`swerebench/sweb.eval.x86_64.peterbe_1776_hashin-74@sha256:e9675431487c5b7f0bcf1a4ece9f4fbc671ade1404160e44ef2f57ff6ad5d053`.
Its clean checkout HEAD matches
`a80c5efbb1630f75a9cfd4492627e9aff051c3e1`. It contains Python 3.9.21,
pytest 8.3.5, packaging 25.0, pip-api 0.0.34 and mock 5.2.0; the record contains
the complete `pip freeze`. The host used Python 3.14.3 and Docker 29.9.2.
The downloaded image fixes installed dependency bytes; its original build is not
yet independently reproduced or its component notices inventoried.

The [dataset card's MIT declaration](https://huggingface.co/datasets/C-lister/ChainSWE/blob/dcaa484eca5b38caca71420712b1b194c1235d6e/README.md)
and [Hashin's MIT license](https://github.com/peterbe/hashin/blob/a80c5efbb1630f75a9cfd4492627e9aff051c3e1/LICENSE)
remain provenance observations. The latter names Peter Bengtsson, copyright
2014–2016. No repository, dataset patches or container layers are redistributed
here. Inherited swe-rebench patch/test rights and image components still need
review. Public requirements, references, tests and this probe are development
material, never secret acceptance checks or an untouched holdout.

No model, paid inference, network-enabled grading, package installation during
grading, treatment comparison, or efficacy claim is part of this probe. It does
not export any placement condition. Source/image downloads are preparation.

## Reproduce

Download the pinned parquet above to a local file and prepare the image once:

```text
docker pull swerebench/sweb.eval.x86_64.peterbe_1776_hashin-74@sha256:e9675431487c5b7f0bcf1a4ece9f4fbc671ade1404160e44ef2f57ff6ad5d053
python -B -m evaluation.hashin_probe PATH/TO/unique.parquet
python -B -m unittest discover -s tests -v
python -B -m evaluation.corpus
```

The probe requires Docker and host PyArrow; it does not install them or download
anything. It executes a fixed command list, never the dataset's `test_cmds`.
The container uses `--pull never`, `--network none`, all capabilities dropped,
`no-new-privileges`, two CPUs, 2 GB memory and 128 PIDs. No host directory,
credentials or Docker socket is mounted. Each child command has a 120-second
timeout and the host run a 900-second timeout. A unique task container name is
removed in `finally`, including on timeout or interrupt; cleanup failures are
reported to stderr. The probe is for pinned trusted public code, not an arbitrary
untrusted-code runner: captured output has no hard byte cap.

Exit zero means the audit completed and produced observations, **not** that
tests or admission passed. A successful phase requires both `returncode: 0` and
`all_required_passed: true`; missing, skipped or failing required IDs cannot
pass. All expected phases must be present. `admission_verified` is always false.
The ordinary repository suite does not invoke Docker or require PyArrow.

## Observed reference and mutant results

All public patches applied unchanged in sequence, starting at the first base.
This carries state forward; it does not reset to the later historical base SHAs.
Each evolving suite checks the accumulated union of declared F2P/P2P node IDs.
The probe separately freezes each previous test tree and reruns it under later
code. It preserves older assertions instead of treating an unchanged test name
as evidence that its assertions survived. No missing or skipped tests occurred.

| Phase | Passed | Failed | Observation |
| --- | ---: | ---: | --- |
| Original base, original tests | 29 | 0 | Environment baseline |
| First test patch, unfixed code | 26 | 3 | Exactly the three declared F2P checks fail |
| First reference | 29 | 0 | All first-step declared checks pass |
| Cached-digest branch falsely logs a download | 28 | 1 | `Tests::test_run` rejects the mutant |
| Download fallback falsely logs a cached hash | 28 | 1 | `Tests::test_get_package_hashes_unknown_algorithm` rejects it |
| Evolving reference steps 2 / 3 / 4 / 5 | 35 / 38 / 76 / 78 | 0 | Accumulated declared IDs remain present and pass |

The mutants each replace one unique logging call in the first reference;
the reference is restored before the next mutation and before carrying on.
These are narrow branch mutants, not an exhaustive adversarial audit of all tasks.

Frozen suites reveal the unresolved cumulative contract boundary:

| Current reference | Frozen earlier suite | Passed / failed |
| --- | --- | --- |
| 2 | 1 | 29 / 0 |
| 3 | 1; 2 | 25 / 4; 31 / 4 |
| 4 | 1; 2; 3 | 25 / 4; 31 / 4; 38 / 0 |
| 5 | 1; 2; 3; 4 | 23 / 6; 29 / 6; 36 / 2; 72 / 4 |

At step 3, the frozen `test_everything`, `test_everything_long`, and
`test_minimal` compare the entire argparse Namespace and reject newly added
`dry_run`/`update_all` fields. `Tests::test_main_packageerrors_stderr` expects
exit code 1 where the new parser behavior returns 2. At step 5, older
`test_get_package_hashes_unknown_algorithm` and `test_run` assert a particular
hash order; the step-5 reference removes the sorting and changes those tests.
The step-4 suite contains class-based and function-based copies, hence four
hash-order failures there. The raw record retains each failure's output.

These observations do not establish that later reference behavior is wrong.
They establish that blindly retaining every old assertion is incompatible with
the supplied sequence. Review must map each changed assertion to the contemporaneous
requirement, separate obsolete expectations from retained invariants, and author
or accept a justified cumulative contract. Do not drop failing tests merely to
obtain a green reference run. The cumulative-regression gate remains pending.

## First-step fact availability inventory

This inventory is a review input, not an authored or approved matched intervention.
The pinned [base `hashin.py`](https://github.com/peterbe/hashin/blob/a80c5efbb1630f75a9cfd4492627e9aff051c3e1/hashin.py)
and the pinned parquet's `bug_fixes[0].problem_statement` are contemporaneous
sources. Reference and test patch fields are evaluator evidence, not eligible
sources for extra knowledge supplied to either arm.

| Fact or expectation | Source and earliest available point | Placement disposition |
| --- | --- | --- |
| Release JSON may already contain a digest for the requested algorithm | Base `get_releases_hashes`; first problem statement explains the prior PyPI change | Eligible at first request; proposed inline anchor is that function, external navigation must identify the same function |
| An absent algorithm uses the download-and-hash fallback | Base `get_releases_hashes`, `except KeyError` branch | Eligible at first request; preserve both branches in any equivalent explanation |
| Verbose output should distinguish using a supplied digest from downloading | First problem statement, interpreted with those base branches | Candidate requirement interpretation; independent review still needed |
| Exact `Found hash for` wording and removal of the returned `url` key | First `test_patch` and reference patch, not explicitly prescribed by the problem statement | Exclude from supplied facts; review whether these assertions overspecify the contract |
| New dry-run support in `run_single_package` | First reference patch includes this beyond the first problem statement | Exclude from first-step facts; investigate inherited patch composition and availability before admitting |
| Update-all, atomic multi-package updates, and hash-order invariance | Later problem statements, steps 3, 4 and 5 respectively | Future requirements; never expose as first-step facts |

The first reference's extra dry-run implementation is an observed patch property,
not proof of an upstream error or that its rationale was available at task 1.
No equivalent external document or inline rendering has been admitted, and no
hidden-check provenance has been certified. Exact wording assertions need review
before treating them as independent measures of requirement satisfaction.

## Remaining gates

The registry records the tested image digest and `execution_verified: true`,
meaning checks actually executed; all nine admission gates remain pending.
Remaining work includes source/patch/image rights, independent image and assertion
review, a justified cumulative contract, mutants for the later tasks, full fact
availability and equivalent-navigation review, controls, semantic deduplication,
and a justified corpus-level feasibility sample. Other repository families still
need executable evidence. No #8 acceptance criterion or offline-only constraint
has been removed.
