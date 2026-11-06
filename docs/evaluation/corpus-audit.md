# Bounded corpus admission audit

**Six candidates are recorded; none is admitted.** This 2026-11-05 metadata audit
advances [#8](https://github.com/AndrewGodlewsky/code-comments/issues/8), which must
remain open. It does not deliver the issue's reviewed, executable placement-pilot
corpus. No benchmark implementation, image, reference solution or evaluator was
executed, and no model or paid inference was used.

The [candidate registry](../../evaluation/corpus-candidates.json) is authoritative
for selected identities, prospective splits, source hashes, evidence links and
pending gates. The [evaluation protocol](../research/evaluation-protocol.md)
continues to own experiment design. This report adds artifact-level evidence to
the [benchmark landscape](../research/benchmark-landscape.md).

## Reproduce the local checks

```text
python -B -m evaluation.corpus
python -B -m unittest discover -s tests -v
```

The validator uses only Python's standard library and does not fetch sources.
Its successful result is `valid: true`, `pending: 6`, `admitted: 0`,
`pilot_ready: false`, `model_calls: 0`. A valid registry is not an approved corpus.
An optional positional JSON path validates another registry; invalid JSON or
admission declarations produce JSON errors and exit code 1.

It checks immutable artifact pins/hashes, required provenance and selection
records, duplicate candidate/task identities, repeated declared solution hashes,
repository split leakage (case-insensitive), step order and base revisions, and
all nine admission gates. An admitted entry needs every gate marked verified with
evidence; environment verification additionally needs an image digest and executed
checks. The CLI always reports `pilot_ready: false`: schema validation cannot
certify sample adequacy, source truth or reviewer independence. Evidence URLs are
checked syntactically, not retrieved or authenticated. Duplicate detection covers
registered IDs/hashes, not semantic equivalence or unregistered benchmark pools.

## What was inspected

The audit used read-only GitHub/HTTPS metadata requests. Source declarations and
task metadata were inspected, not outcome tables or treatment runs. Primary
artifacts were pinned before extracting the records:

| Artifact | Immutable revision | Inspection |
| --- | --- | --- |
| [SlopCodeBench problems](https://github.com/gabeorlanski/scb-problems/tree/9cd9ca3a51c3d3e2a99d2488a25baf73a2204451) | `9cd9ca3a51c3d3e2a99d2488a25baf73a2204451` | Root README/LICENSE; three configurations; checkpoint 1–4 specifications; test-tree listings and conftest/checkpoint 1–2 test structure |
| [ChainSWE dataset](https://huggingface.co/datasets/C-lister/ChainSWE/tree/dcaa484eca5b38caca71420712b1b194c1235d6e) | `dcaa484eca5b38caca71420712b1b194c1235d6e` | Card, file metadata, first three `unique` rows, task requirement excerpts, base commits, ordered IDs, image tags, commands and F2P/P2P list counts |

Each SlopCodeBench entry hashes its actual configuration bytes. These are hashes
of the configuration, not of the whole problem tree; the commit pins that tree.
All three configurations declare four checkpoints. Test files' presence and
names do not establish correct assertions or cumulative execution.

ChainSWE's `data/unique.parquet` was read in memory (7,959,933 bytes) with the
environment's already-installed PyArrow; it was not installed as a project
dependency or retained in this repository. Its computed SHA-256 matched the
[upstream LFS metadata](https://huggingface.co/api/datasets/C-lister/ChainSWE/tree/dcaa484eca5b38caca71420712b1b194c1235d6e/data):
`f7de0d66b64a9d5c28921fba2bbd51b5131dae8d5c789e03e61c09e67fc355fe`.
The parquet was decoded as data; embedded patches and test patches were neither
executed nor copied into this repository. Requirement excerpts and test metadata
were inspected, not full reference solutions or a complete assertion-to-contract
review. The current-row API was a discovery aid; the committed metadata was
extracted again from the pinned parquet.

The pinned [ChainSWE card](https://huggingface.co/datasets/C-lister/ChainSWE/blob/dcaa484eca5b38caca71420712b1b194c1235d6e/README.md)
reports 213 unique sequences and 956 bug-fix occurrences; its length-specific
splits total 376 sequences and 1,504 occurrences. It says `unique` is a union, not
extra data, and points to `C-lister/SWE-Edit`. These are release declarations,
distinct from the paper's 100-chain sample and the earlier research's Microsoft
SWE-Edit pointer. No harness revision is accepted by this audit.

## Selection and prospective splits

Three named SlopCodeBench problems were selected for different requirement
families. ChainSWE inspection was bounded to the first three rows of the pinned
`unique` split, a convenience sample. The count of six is an audit workload bound,
not a statistical sample-size justification. Selection, split and rationale are
recorded before any model or treatment outcome inspection.

| Candidate | Prospective split | Reason to investigate; unresolved limitation |
| --- | --- | --- |
| SlopCodeBench `file_backup` | Development | Event ordering, scheduling and incremental backup state; reference/strict cumulative scoring not executed |
| SlopCodeBench `layered_config_synthesizer` | Development | Cross-file precedence, fragments and changing warning formats; no reviewed matched fact inventory |
| SlopCodeBench `file_merger` | Development | Stable sorting and representation changes, including replacement of the flat-input restriction by nested types; no demonstrated low-context control |
| ChainSWE `qutebrowser_qutebrowser_20230926_46a44f9be4a580ff` | Held-out reservation | Five Qt/version-workaround tasks; reserve the whole repository for later public confirmation, with environment and contamination limits |
| ChainSWE `peterbe_hashin_20180808_fa5563e40100136f` | Pilot | Five packaging CLI tasks, including atomic updates and hash-order invariance; inherited commands install dependencies during testing |
| ChainSWE `internetarchive_openlibrary_20240424_4766147f25835197` | Pilot | Five identifier/catalog/affiliate/import tasks; per-issue checks span different modules and do not establish cumulative coverage |

All SlopCodeBench tasks stay in development because they share a source
repository; their distinct problem names do not justify repository-independent
splits. ChainSWE split ownership uses the underlying application repository, not
the shared dataset repository. The reservation is administrative: the qutebrowser
tasks and solutions are public, and task/test metadata was inspected here. It is
not a secret, untouched or contamination-free holdout. Fresh repository families
and authored sequences remain necessary for stronger confirmation claims.

No candidate was selected because comments won. No additional authored fixture
was added: the existing [retry-policy diagnostic](README.md) already exercises
changing constraints and explicit mutants, and another similar toy would not
resolve the real-corpus acceptance gaps. These candidates propose coverage; they
do not establish representative cross-file work, genuine obsolete rationale, or
a suitable low-context control set. Other tasks were outside this bounded audit,
not excluded because of observed model performance. All six remain pending rather
than being silently dropped for unresolved environments or rights.

## Rights and execution gates

These are observed source declarations, not clearance for redistribution.
SlopCodeBench's pinned [LICENSE](https://github.com/gabeorlanski/scb-problems/blob/9cd9ca3a51c3d3e2a99d2488a25baf73a2204451/LICENSE)
contains Apache 2.0, while its pinned
[README badge](https://github.com/gabeorlanski/scb-problems/blob/9cd9ca3a51c3d3e2a99d2488a25baf73a2204451/README.md)
says MIT. This confirms the discrepancy already identified in the benchmark
landscape. Resolve the declaration and artifact-specific notices before reuse.

The ChainSWE card declares MIT. At their recorded base commits, the underlying
repositories contain [GPL v3 license text for qutebrowser](https://github.com/qutebrowser/qutebrowser/blob/690813e1b10fee83660a6740ab3aabc575a9b125/LICENSE),
[MIT text for hashin](https://github.com/peterbe/hashin/blob/a80c5efbb1630f75a9cfd4492627e9aff051c3e1/LICENSE),
and [AGPL v3 text for Open Library](https://github.com/internetarchive/openlibrary/blob/5f7d8d190e2f0d837545e582fd5db99aae51a979/LICENSE).
These observations do not inventory every file, inherited source-benchmark test
patch, dataset right, or container component. Those rights layers remain pending.

SlopCodeBench declares Python 3.12+ and the selected configurations list PyYAML;
`file_merger` additionally lists PyArrow. ChainSWE provides image tags but no
verified image digests in this audit. Hashin's recorded commands include apt/pip
installation; replaying them unchanged would not be a reproducible network-free
grading phase. Upstream commands are inert provenance strings, not instructions
executed by the validator. Images, toolchain pins, offline dependency closure,
resource costs, baseline pass/fail states and strict cumulative checks remain
unverified for all six candidates.

## Remaining acceptance work for #8

1. Resolve artifact-level rights; pin and reproduce candidate environments safely.
   Prove known-good states and adversarial mutations under cumulative regressions.
2. Map each exposed fact to its contemporaneous source and earliest availability;
   keep future requirements, reference patches and hidden checks out of both arms.
   Review equivalent external navigation and every hidden assertion independently.
3. Add a justified low-context control, audit changing/obsolete constraints, and
   verify coverage across actual repositories instead of relying on these labels.
4. Deduplicate against all development/pilot/confirmation sources, including
   solution-equivalent tasks and inherited benchmark aliases. The registry's
   mechanical checks cannot establish absence of memorization or semantic leakage.
5. Select the executable feasibility sample before outcomes, record environment
   exclusions and limitations, and obtain independent full corpus review.

The fixture tests validate local plumbing. They are not candidate execution or
efficacy evidence. Keep #8 open, retain its recoverable branch/worktree, and retain
the user's offline-only constraint; this audit does not authorize a model campaign.
