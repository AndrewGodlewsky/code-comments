# Corpus admission audit implementation plan

> Implemented by the assigned corpus agent; root coordinates Git and independent review.

**Goal:** Make the bounded metadata audit for #8 inspectable and prevent unchecked
candidates from being mistaken for an admitted pilot corpus.

**Architecture:** A JSON registry records upstream identities, evidence, prospective
splits and explicit admission gates. A standard-library validator checks its
structure and cross-record constraints without fetching or executing artifacts.

**Spec:** [Issue #8](https://github.com/AndrewGodlewsky/code-comments/issues/8),
bounded to offline admission work by the coordinator. Full corpus acceptance stays
open. Existing fixture behavior and runner implementation are outside this slice.

**Constraints:** No model calls, installed corpus, executed upstream code, Git
mutations or dependencies added by this agent. Metadata HTTP reads are allowed.

## Implementation and checks

- [x] Audit three small SlopCodeBench task descriptions and three ChainSWE rows,
  recording immutable source revisions and rights evidence in
  `evaluation/corpus-candidates.json` before any treatment outcome is available.
- [x] Add failing `tests/test_corpus.py` cases for duplicate candidates/tasks,
  repository split leakage, malformed/missing provenance, unknown gates, false
  readiness, missing evidence, and CLI invalid-input handling.
- [x] Implement `validate_registry(data: object) -> list[str]` and a JSON CLI in
  `evaluation/corpus.py`. Validation errors must not silently admit a candidate.
- [x] Run `python -B -m unittest discover -s tests -v` and
  `python -B -m evaluation.corpus`; preserve the original 12 offline tests.
- [x] Write `docs/evaluation/corpus-audit.md` with methods, selection rationale,
  inspected/unverified boundaries, limitations and remaining #8 criteria.
- [x] Hand exact changed files and evidence to root for checkpoint and independent
  review; keep #8 open and retain its branch until its purpose is fulfilled.

## Review focus

Missing or malformed JSON fields must fail validation rather than crash. Repository
identity, not just benchmark chain name, governs split separation. Duplicated issue
IDs and declared solution hashes need cross-candidate checks. A public reserved
split is not evidence of uncontaminated held-out evaluation. Pinned declarations
and existing test files are not execution evidence or rights clearance.

Validation: 26 tests passed (14 admission tests plus the original 12 offline tests).
The registry reports six pending entries and zero admitted. Independent review and
all Git/tracker operations remain with root; full issue #8 acceptance is incomplete.
