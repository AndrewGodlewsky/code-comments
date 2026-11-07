# Candidate repositories for real-history replay

Status: metadata research, 2026-11-07. Nothing from these repositories was
installed or executed, and no model was run. This document adds to the #8 corpus
registry; it does not admit anything to it. Admission (rights, pinned environments,
cumulative contracts, fact provenance, leakage review, independent review) stays
with the registry process on `agent/8-corpus-audit`. See
`docs/evaluation/corpus-audit.md` and `evaluation/corpus-candidates.json` on that
branch. This document does not repeat those checks.

**Short answer.** The #8 registry has no medium-size real repository with recent
history. Five new suggestions fill that gap: **narwhals**, **cyclopts**,
**jsonargparse** and **omegaconf** for the medium tier, and **nilearn** for the
large tier. Each has 10 to 15 consecutive qualifying PRs after July 2026, which is
after the June 2026 training cutoff of current frontier models. The top
recommendation is **narwhals**. Almost every public-API change has to be repeated
in each backend directory, which is exactly the "this affects that" relationship
the user's theory is about.

## How the corpus will be used

The repository starts at an older commit. A fresh agent session then receives
each later change request in order, taken from a real merged PR or its linked
issue. Each step is graded by the tests the developers added in that PR, plus the
existing suite. The arms differ in how context is maintained: code only, an
AI-maintained `docs/` folder, or inline comments written by the skill. Weaker and
frontier models act as readers. See the "fuller theory" section of `intent.md`
and the 2026-11-07 tier proposal on issue #8.

## Selection criteria

1. **Python.** At most one non-Python candidate, and only if it is exceptional.
   None was needed.
2. **Size.** Medium tier: about 5k-50k lines of source. Optionally one candidate
   for the large tier (100k+ lines in total).
3. **Tests.** A real test suite that probably runs offline, judged from the CI
   workflows and test configuration only.
4. **History.** Merged PRs that each change source code and add or change tests,
   ideally linked to an issue with a written rationale. The count must hold in a
   recent contiguous window.
5. **Cross-module changes.** PRs regularly touch several source files or modules,
   with non-obvious constraints between them.
6. **Contamination.** Under about 2-3k stars and substantial activity in 2026.
7. **License.** Permissive: MIT, BSD or Apache (ISC also counts as permissive).
8. **Bonus.** An existing `docs/` folder, ADRs, rich comments, or agent
   instruction files. These affect how each arm is seeded.

**Definitions used in the counts.**

- A **qualifying PR** is merged into the default branch, by an author that is not
  a bot, and changes at least one non-test Python source file and at least one
  test file. Files under `docs/`, `examples/`, `benchmarks/`, `scripts/` and
  `.github/` are not counted as source.
- **Multi-file** means at least two source files changed. **Linked** means
  GitHub's closing-issue reference, or `fixes/closes/refs #N` in the PR body.
- **LOC** counts non-blank Python lines in a depth-1 clone of the default branch,
  taken 2026-11-07. Vendored and generated code is excluded where noted. The
  windows' base commits will be somewhat smaller.

## Already in the #8 registry

Registry ids are from `evaluation/corpus-candidates.json` on
`agent/8-corpus-audit`. All six are `pending`. Only the Hashin entry has been run
(Docker image, offline).

| Registry id | Meets | Lacks for this replay design |
| --- | --- | --- |
| `scb:file_backup`, `scb:layered_config_synthesizer`, `scb:file_merger` | Python; offline pytest checkpoints (Python 3.12, PyYAML, plus PyArrow for `file_merger`); good controlled invariants | Not a real repository history. The agent builds code from specifications, so there are no real PRs, issues or existing docs. It starts tiny, far below 5k lines. LICENSE (Apache-2.0) and README badge (MIT) conflict. All three share one source repository, so they stay in development. |
| `chainswe:peterbe_hashin_20180808_fa5563e40100136f` | Python; MIT; 107 stars; offline execution shown in a pinned image; F2P checks behave correctly | **Size and structure.** About 785 non-blank source lines in essentially one module (`hashin.py`), so no cross-module effects. **Recency.** The sequence is from 2018, is public in ChainSWE and SWE-rebench, and is very likely memorised. Only 1 qualifying PR in 2026 (20 merged, 14 by bots). No docs folder. Frozen-assertion conflicts are already recorded in the registry. |
| `chainswe:qutebrowser_qutebrowser_20230926_46a44f9be4a580ff` | Python; real multi-module code; large tier (about 4.0 MB of Python, 2.3 MB of it outside tests, roughly 60-70k source lines, estimated from byte size); has `doc/` | **GPL-3.0**, which fails criterion 7. **11.7k stars**, and the 2023 history is likely memorised. A Qt/PyQt GUI environment. Only 19 merged PRs in 2026. Reserved as held-out, but the registry itself says it is not contamination-free. |
| `chainswe:internetarchive_openlibrary_20240424_4766147f25835197` | Python; very active (1,249 merged PRs in 2026); large tier (about 5.3 MB of Python, roughly 80-90k source lines, estimated from byte size); has `docs/`, `AGENTS.md`, `CLAUDE.md` and `.claude/` | **AGPL-3.0**, which fails criterion 7. **6.8k stars.** Python and JavaScript. Heavy Docker/infogami environment. The 2024 base is likely memorised. The registry notes that its per-issue checks span modules without cumulative coverage. |

**Gaps that the new suggestions fill.**

1. No real repository in the 5-50k medium tier.
2. No history from after the cutoff: every ChainSWE sequence predates 2025.
3. No permissively licensed real repository larger than Hashin.
4. No candidate whose ordinary PRs regularly cross module boundaries.
5. No real repository with both a `docs/` folder and recent history. That pairing
   is needed to seed the docs-folder arm from what the project actually kept.

## New suggestions: comparison

Measured 2026-11-07 with `gh api` and depth-1 clones. "Qualifying 2026" counts PRs
merged from 2026-01-01 to 2026-11-07. Where marked ≥, the GraphQL fetch was
capped at 300 PRs, so the figure is a lower bound.

| Repo | Stars | License | Source LOC (tests) | Test framework | Offline likelihood | Qualifying 2026 (multi-file / linked) | Proposed window: qualifying (multi-file / linked) | Cross-module evidence | Docs and agent files |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| [narwhals-dev/narwhals](https://github.com/narwhals-dev/narwhals) | 1,747 | MIT | about 46k, of which about 23k is in 11 backend packages (34k) | pytest with `--constructors=` selection | High once wheels are cached. CI runs pandas, pyarrow, polars, duckdb and sqlframe on Linux and Windows. pyspark, ibis and modin have separate optional workflows. | ≥113 (≥85 / ≥48); 470 merged in total by search | 15 (12 / 10) | Each API change must be mirrored across `_arrow`, `_pandas_like`, `_polars`, `_duckdb`, `_ibis`, `_spark_like`, and others. For example, #3859 touches 6 source files in 5 directories. | `docs/` (52 pages), `AGENTS.md`, `CONTRIBUTING.md` |
| [BrianPugh/cyclopts](https://github.com/BrianPugh/cyclopts) | 1,293 | Apache-2.0 | about 22.8k (44k) | pytest | High. Pure Python dependencies, and CI runs on Ubuntu, macOS and Windows. | 147 (77 / 36) | 12 (7 / 5) | Parsing, binding, conversion, config sources and help rendering interact. For example, #991 touches 6 files in 4 directories. | `docs/` (Sphinx, 59 pages), `CONTRIBUTING.md`; 8% comment lines |
| [mauvilsa/jsonargparse](https://github.com/mauvilsa/jsonargparse) (formerly `omni-us`) | 434 | MIT | about 14.8k (24k) | pytest; tox in CI | High. HTTP tests use `responses` mocks or skip when it is missing. CI also runs on Windows. | 138 (101 / 22) | 12 (10 / 2) | Flat package `_core`, `_typehints`, `_signatures`, `_loaders_dumpers` and others. Typical PRs touch 5-10 of them. | No `docs/`. Has `DOCUMENTATION.rst` and `sphinx/` (including a migration guide). A changelog entry is required in each PR. |
| [hydra-ecosystem/omegaconf](https://github.com/hydra-ecosystem/omegaconf) | 2,443 | BSD-3-Clause | about 9.9k, excluding the 10.2k-line vendored ANTLR runtime (31k) | pytest via nox; CircleCI | Medium-high. Offline, but the ANTLR parser is generated at build time with **Java** (CI installs `openjdk-11-jre`). | 82 (42 / 66) | 15 (13 / 13) | Nodes, containers, the grammar/interpolation layer and structured-config unions. Revives issues from 2020-2022, for example #1373 closing #459. | `docs/`, `NEWS.md`, `AGENTS.md`, `.github/copilot-instructions.md` |
| [nilearn/nilearn](https://github.com/nilearn/nilearn) (large tier) | 1,453 | BSD-3-Clause | about 76k (46k), about 122k in total | pytest via tox | Medium-high. `nilearn/datasets/tests/conftest.py` auto-mocks HTTP. Heavy scientific stack, plus `pytest-mpl` for plots. | ≥97 (≥60 / ≥45); 519 merged in total by search | 15 (8 / 10); 13 usable tasks | Maskers, GLM, surface, plotting and reporting. For example, #6472 touches 3 directories. | `doc/` (114 pages), `AGENTS.md`, `CLAUDE.md` |

Reserve candidate: [hgrecco/pint](https://github.com/hgrecco/pint). It has 2,824
stars, a BSD-style license (GitHub reports `NOASSERTION`; the LICENSE text is the
BSD 3-clause form), about 15.6k source lines, a `docs/` folder, 108 qualifying 2026
PRs (32 multi-file, 76 linked) and an offline numpy-based test suite. It is held
in reserve because it sits at the star ceiling, most PRs touch one source file, and
33 PRs were merged on 2026-07-26 alone (24 of them qualifying), so their merge
order needs checking.

## Picks

### 1. narwhals: top recommendation

**Why it fits.** narwhals is a compatibility layer whose core invariant is
*behavioural parity across backends*. Null propagation, ordering, index alignment
and dtype rules must hold in pandas-like, pyarrow, polars, duckdb, ibis and spark
alike. The code does not enforce that invariant from any single place, so it is
easy to miss when editing one backend. That is the gap the theory says comments
at the point of edit will close. Recent PRs show it directly:

- #3859, "`is_in` was not preserving nulls": `_arrow`, `_ibis`, `_pandas_like`,
  `_spark_like` and the public `expr.py` and `series.py`.
- #3863: 8 directories.
- #3843: 12 source files in 9 directories.

Issues usually state the expected behaviour, and 10 of the 15 window PRs are
linked to one. The repository already has a substantial `docs/` folder and an
`AGENTS.md`.

**Risks.**

- The environment is heavier: pandas, polars, pyarrow, duckdb and sqlframe
  wheels. Restrict the graded runs to the constructors CI uses on Windows, and
  exclude pyspark, ibis and modin unless an image provides them.
- Size is about 46k lines, at the top of the medium tier, so reading costs more.
- The window spans 59 merged main-branch PRs, so 44 intermediate PRs (chores, bots
  and docs) must be applied as ground truth between tasks.
- The existing `AGENTS.md` and `docs/` must be held constant across arms, or
  stripped from all of them.
- Several 2026 contributors appear in more than one repository here, which
  suggests agent-assisted PRs. This is an inference, not verified.

**Proposed window: 15 qualifying PRs.**

- Merged 2026-07-10 to 2026-08-20.
- PRs #3756, #3771, #3791, #3794, #3805, #3697, #3813, #3855, #3862, #3859,
  #3866, #3865, #3863, #3856, #3843.
- Base: `3c02b89f27e0` (first parent of #3756's squash commit `dcbbf22fd6f4`).
- End: `799eabfc8d2a` (#3843).
- Treat #3813 (lockfile and lint sweep) as an intermediate commit, not a task,
  which leaves 14 tasks.

**Contamination trade-off.** With 1.7k stars, the older code is probably in
training data. The window starts after June 2026, so the specific fixes post-date
current frontier training. Mid-popularity also gives enough issue volume for a
second window later.

### 2. cyclopts

**Why it fits.** A CLI framework with clearly separated layers: tokenisation,
argument binding, type conversion, config-file and environment sources, and help
or completion rendering. Many fixes are constraints that cross those layers. For
example, #1004 "reject a config `null` for a type that does not allow None", #1015
"stop silently dropping unknown keys on a class-or-dict union", and #991 (6 files
in 4 directories). It is Apache-2.0, has a pure Python dependency stack, and runs
CI on Ubuntu, macOS and Windows. It is the **cheapest environment** of the five,
and a good first pilot.

**Risks.**

- One maintainer authors most qualifying PRs (56 of 80 on `main` since July). The style is
  consistent, but the sample is narrow.
- PR bodies are short. Only 5 of the 12 window PRs link an issue, so the other
  change requests come from PR titles and bodies.
- The project mixes merge and squash commits. Replay along `--first-parent`.
- Avoid #959 ("V5 Release", +12.6k lines, merged from `v5-develop`).

**Proposed window: 12 qualifying PRs.**

- Merged 2026-10-12 to 2026-10-22: #1004, #1006, #1010, #1001, #1005, #1008,
  #992, #991, #1018, #1021, #1019, #1015.
- 17 main-branch PRs merged in those dates.
- Base: `6feee65cc6f2` (parent of #1004's merge `7063e4f0445b`). End:
  `6bb7cf329b61` (#1015).
- A longer alternative, before V5: 15 qualifying PRs from #825 to #862,
  2026-05-25 to 2026-07-19 (9 multi-file, 7 linked). Base `e297647b12b7`, end
  `a9e415985b36`. It is partly before the cutoff.

**Contamination trade-off.** With 1.3k stars, the October 2026 window falls after
the cutoff and after a major-version rewrite. This is the least memorisable
combination after jsonargparse.

### 3. jsonargparse: lowest contamination

**Why it fits.** With **434 stars**, this is the least likely of the five to be
memorised. It is MIT-licensed and builds argument parsers from type hints and
signatures. Typical PRs change 5-10 private modules together (`_core`,
`_typehints`, `_signatures`, `_loaders_dumpers`, `_subcommands`, `_common`). For
example, #997 "Change default parser mode to json" touches 5 source modules, the
docs, the changelog and 4 test files. Breaking-change PRs carry explicit rationale
and a v5 migration guide (`sphinx/migrate_v5.rst`), which is good material for the
docs-folder arm.

**Risks.**

- **One author** wrote 78 of the 80 qualifying PRs since July.
- PRs are **large**, often +500 to +1,500 lines. Steps may be too hard for weaker
  readers in every arm, and a corpus where every arm fails cannot detect a
  placement effect.
- Only 2 of the 12 window PRs link issues. The change requests rely on detailed
  PR bodies.
- No `docs/` folder. Documentation lives in one large `DOCUMENTATION.rst`, which
  changes how the docs arm is seeded.
- The repository moved from `omni-us/jsonargparse`. GitHub search rejects the old
  name.

**Proposed window: 12 qualifying PRs.**

- Merged 2026-09-24 to 2026-10-08: #986, #990, #991, #993, #995, #1000, #997,
  #1002, #1001, #1004, #1008, #1007.
- 14 main-branch PRs merged in those dates.
- Base: `ed8211eef279` (parent of #986's squash `275be4899916`). End:
  `f4b420a355ef` (#1007).
- Alternative: 15 PRs from #958 to #665, 2026-08-19 to 2026-09-14. It contains
  #969, a 3,000-line deprecation removal, which should be treated as an
  intermediate commit.

**Contamination trade-off.** This is the strongest contamination control. The cost
is a single-maintainer style and large steps.

### 4. omegaconf: strongest written rationale

**Why it fits.** In 2026 the original author revived the project and is closing
issues from 2020-2022 with focused PRs. In the window, **13 of 15** PRs are linked
to issues that state the user problem, and several record design decisions in the
PR body. For example, #1373 "Deprecate implicit conversion on direct assignment"
fixes #459. The domain is non-obvious: interpolation grammar, structured-config
unions, merge semantics and node typing interact. A minor-looking change to
`nodes.py` alters merge or interpolation behaviour elsewhere. The repository has
`docs/`, `NEWS.md`, `AGENTS.md` and Copilot instructions.

**Risks.**

- **Java is required** to generate the ANTLR parser (`build_helpers`). Bake a JRE
  into the image, or pre-generate the parser at each step.
- With 2.4k stars and use through Hydra, the **base code is widely memorised**,
  even though the 2026 fixes are new.
- One author wrote 38 of 43 qualifying PRs since July, and `AGENTS.md` shows the
  maintainer works with coding agents.
- The October window includes release-engineering PRs (#1411, #1412) to skip.
- Within a day the merge order is ambiguous (#1353 and #1354 merged on the same
  day). Derive the order from first-parent history.

**Proposed window: 15 qualifying PRs.**

- Merged 2026-07-24 to 2026-09-28: #1354, #1353, #1356, #1358, #1361, #1359,
  #1367, #1371, #1376, #1375, #1374, #1373, #1377, #1379, #1378.
- 21 main-branch PRs merged in those dates.
- Base: `a6f45ae15caa` (parent of #1354's squash `8126be33f254`). Check whether
  #1353 landed first. End: `8986124fa62b` (#1378).
- Treat #1367 (license packaging) and #1371 (link and workflow update) as
  intermediate commits, which leaves 13 tasks.

**Contamination trade-off.** The fixes are new, but the old issue threads have been
public for years. A model may already know the requested behaviour from the issue
discussion. Hide issue comments posted after the PR was opened, as the history
leakage controls in the protocol require.

### 5. nilearn: large tier

**Why it fits.**

- About 76k source lines and 46k test lines, BSD-3-Clause, 1.45k stars.
- Very active: 519 merged PRs in 2026.
- A real multi-package scientific library: maskers, GLM, surface, plotting,
  reporting and datasets.
- Dataset tests use an **auto-used HTTP mock**, which is strong offline evidence.
- Large `doc/` tree plus `AGENTS.md` and `CLAUDE.md`.

**Risks.**

- Heavy environment: numpy, scipy, scikit-learn, nibabel, matplotlib and
  `pytest-mpl` image comparisons. Plot tests can be platform-sensitive.
- The window has 64 merged main-branch PRs for 15 qualifying ones.
- Two qualifying PRs are sweeps and should be intermediate commits: #6482
  (docstring fixes across 88 files) and #6545 (sklearn bump).
- Many single-file fixes. The cross-module share is lower than narwhals.

**Proposed window: 15 qualifying PRs, 13 tasks.**

- Merged 2026-08-14 to 2026-09-05: #6448, #6472, #6482†, #6501, #6517, #6519,
  #6505, #6503, #6423, #6522, #6520, #6529, #6531, #6546, #6545†.
- † means an intermediate commit, not a task.
- Base: `7f6805505334` (parent of #6448's squash `6aec72023924`). End:
  `734e863a6309` (#6545).

**Contamination trade-off.** The large, domain-specific code is moderately known.
The window is after the cutoff.

## Top recommendation

Start the medium tier with **narwhals**, because the theory predicts the largest
effect where cross-module parity matters. Pair it with **jsonargparse** as the
low-contamination check. Use **cyclopts** for the first wiring pilot, because its
environment is cheapest and runs natively on Windows. Add **omegaconf** if the
JRE is acceptable in the image, for its issue-backed rationale. Add **nilearn**
when the large tier starts. Every pick still has to pass the #8 admission gates.
These windows are proposals, chosen before any treatment outcome was seen.

## Rejected candidates

| Repo | Reason |
| --- | --- |
| schemathesis/schemathesis | 3.75k stars, over the ceiling. Very active (2,284 merged PRs in 2026). |
| copier-org/copier | 3.68k stars. |
| commitizen-tools/commitizen | 3.55k stars. |
| koxudaxi/datamodel-code-generator | 4.05k stars, and about 33 MB of Python including generated fixtures. |
| pydantic/pydantic-settings | Fits on paper: MIT, 1.5k stars, 117 qualifying 2026 PRs, 61 linked. But only about 5.9k source lines, most PRs touch one source file (41 multi-file), and the pydantic family is high-profile. Kept as a small-tier fallback: the 15-PR window #740..#786 (Jan-Feb 2026) has 8 multi-file and 13 linked. |
| 15r10nk/inline-snapshot | Good linkage (15 of 15 in the best window) and `AGENTS.md`, but only about 6.5k source lines and 41 merged PRs in 2026. That window spans February to July and includes #352 (+3.8k/-3.4k) and a docs rewrite. Its downstream tests clone external repositories, though only through an optional script. |
| hgrecco/pint | Reserve (see above). Star ceiling, mostly single-file PRs, batch merges on the same day. |
| fsspec/filesystem_spec | 224 qualifying, but only 22 multi-file. Changes stay inside one implementation. |
| python-poetry/tomlkit | 82 qualifying, only 5 multi-file. |
| python-attrs/cattrs | 27 qualifying, 7 multi-file. |
| agronholm/anyio | 2.57k stars. 107 qualifying, 21 multi-file. Socket and thread tests. |
| pvlib/pvlib-python | Good culture and docs, but only 14 of 53 qualifying PRs are multi-file. |
| python-babel/babel | Mostly single-file. Large CLDR data dependency. |
| python-semantic-release, polyfactory, bump-my-version, mkdocstrings/griffe | Fewer than 25 qualifying PRs in 2026, and few are multi-file. |
| pybamm-team/PyBaMM | Large tier: about 90k source lines and 137 qualifying PRs, but now a monorepo with C++ SUNDIALS solvers. Some tests use `DataLoader` (pooch downloads). It carries AGENTS, CLAUDE, GEMINI and QWEN instruction files. Second choice for the large tier. |
| aeon-toolkit/aeon, skrub-data/skrub, sunpy/sunpy, dask/distributed | Heavy numba or ML stacks, remote-data tests (sunpy, skrub datasets), or flaky multi-process tests (distributed, with only 7 linked qualifying PRs). |
| qutebrowser, openlibrary (already in the registry) | GPL-3.0 and AGPL-3.0; over the star ceiling. See the registry table. |

## Search log

1. Read `intent.md` (fuller theory and scope clarification), issue #8 and its
   comments, and `docs/research/benchmark-landscape.md`.
2. Following the coordinator's correction, read `docs/evaluation/corpus-audit.md`,
   `docs/evaluation/hashin-preflight.md` and `evaluation/corpus-candidates.json`
   on `agent/8-corpus-audit` with read-only `git show` and `gh api`. That branch
   was not modified.
3. `gh search repos --language=python --stars=400..2500 --license={mit,apache-2.0,bsd-3-clause} --updated=>2026-10-01`.
   The results were mostly applications and ML research code. They were used for
   leads only (omegaconf, nilearn, PyBaMM, skrub and others).
4. Built a list of library candidates from the search and prior knowledge, then
   checked each one with `gh api repos/...` (stars, license, last push, language
   bytes). A `search/issues` query counted 2026 merged PRs.
5. Fetched up to 300 recent merged PRs per repository with GraphQL: files,
   additions, closing issues, body, author and base branch. Classified them with
   the definitions above and scored windows of 12-15 consecutive qualifying PRs by
   multi-file and linked counts. Windows were restricted to merges from July 2026
   onward where possible.
6. Depth-1 clones went to the session scratch directory, with hooks disabled and
   Git LFS smudging skipped. These clones were used only to count lines and to
   inspect CI workflows, `pyproject` and test configuration. Nothing was executed,
   built or installed.
7. Spot-checked PR bodies (omegaconf #1373, jsonargparse #997, narwhals #3859)
   and merge strategies (squash versus merge commits) through the API.
   Window base and end SHAs came from each PR's `merge_commit_sha` and its first
   parent.

## Unverified items

- **Offline status.** No suite was run, so every "offline likelihood" is a
  judgment from configuration. Each still needs the registry's pinned-image
  preflight, as Hashin had.
- **Merge order within a day.** Windows are sorted by merge date only. Re-derive
  the exact order and base commits from `git log --first-parent` before use.
- **Lower-bound counts.** Counts for narwhals and nilearn come from the 300 most
  recently updated PRs (marked ≥).
- **Link counts.** "Linked" is a heuristic: closing references plus body
  patterns. Issue quality was spot-checked, not reviewed.
- **Benchmark overlap.** Whether any window overlaps SWE-rebench, SWE-Gym or
  ChainSWE task pools was not checked. The registry's deduplication gate owns
  that.
- **AI-assisted PRs.** The claim that some 2026 PRs are agent-assisted is an
  inference from contributors who appear in several repositories, a
  `claude/...` branch name in pint, and `copilot-swe-agent` in inline-snapshot.
- **License clearance.** Licenses are GitHub's SPDX detection, with pint's
  LICENSE text read directly. Neither is legal clearance.
