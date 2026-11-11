# Ideation, 2026-11-11: which adjacent skills to build

This records how the four incubator skills were chosen (issue
[#50](https://github.com/AndrewGodlewsky/code-comments/issues/50)). The raw output is in
[2026-11-11-candidates.json](2026-11-11-candidates.json): every candidate's problem,
evidence, behaviour and case design, the ideas that were dropped, and each judge's
scores and reasons.

## Method

1. **Five ideators.** Each read the project's intent, ADR 0001, the shipped skill, the
   hygiene and activation evals, and the research index. Each then proposed three
   skills from one angle:
   - **reader:** helping a later, possibly weaker model use the context that already
     exists;
   - **drift:** the founding two-sources-of-truth problem;
   - **search:** ADR 0001's grep-based discovery, and #34;
   - **failures:** what the recorded evals show agents getting wrong;
   - **lifecycle:** the moments when context is lost, such as review, hand-off, moves
     and deletions.
2. **One merger.** It clustered the 15 ideas into 10 distinct candidates and checked them
   against the hard constraints:
   - no index, memory store or lookup service;
   - not a rewording of the shipped skill;
   - evaluable offline with mechanical graders;
   - plausible headroom over a bare model.

   No whole idea broke a constraint. Some parts of ideas were dropped, and reserve
   cases were set aside; the JSON lists them under `dropped`.
3. **Three judges,** each with one lens, scored every candidate from 1 to 10:
   - **intent:** does it serve the user's stated problems?
   - **rigour:** can a discriminating, mostly code-graded eval be built tonight?
   - **skeptic:** overlap, ADR conflicts, likely null result, noise, activation.

   Each judge checked the claims it relied on against the repository.

The ideators' web findings were not audited at this stage. Each chosen skill's
`research.md` verifies the sources it uses.

## Scores

| Id | Candidate | Intent | Rigour | Skeptic | Total | Outcome |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | `constraint-sweep`: before changing behaviour, read what other files' comments, docstrings and tests say about it | 9 | 8 | 7 | 24 | **Built** |
| C2 | `verify-before-relying`: check a comment's claim against the code before building on it | 8 | 7 | 6 | 21 | **Built** |
| C3 | `change-drift-sweep`: after a change re-values or renames something, find prose still stating the old value | 8 | 7.5 | 5 | 20.5 | **Built**, with C7's review mode as a next step |
| C6 | `fold-docs-inline`: slim a docs page by giving each code-owned fact one home beside the code | 9 | 5.5 | 5 | 19.5 | **Built**, scoped to one named page |
| C4 | `workaround-expiry`: remove a workaround only when its stated removal condition is verifiably met | 5 | 7 | 6.5 | 18.5 | Runner-up |
| C7 | `diff-comment-review`: report comments a finished diff made false outside its hunks | 7 | 6 | 5.5 | 18.5 | Folded into C3 as a later review mode |
| C8 | `cross-file-pointers`: write a fact once at the owner and point to it by exact symbol | 7 | 6 | 4 | 17 | Not built: close to the shipped skill's "one home, point to it" rule |
| C5 | `comment-change-guard`: diff comments after editing and restore still-true ones | 4 | 6.5 | 4 | 14.5 | Not built: enforces the shipped skill's own rules (#21, #48) |
| C10 | `context-tags`: an opt-in tag convention (`WHY:`, `CONSTRAINT:`) with a lint | 5 | 4.5 | 3 | 12.5 | Not built: #34 is parked as later research |
| C9 | `session-handoff-inline`: move what a session learned into comments at hand-off | 4 | 4 | 3 | 11 | Not built: overlaps the user's own memory layer |

## Why these four

- **Two judge picks plus one rescue.** C1 and C2 are on every judge's list of four. C3
  is on two. C6 ranks fourth because it is the most direct attack on the founding
  problem (intent judge: 9). The rigour and skeptic judges marked it down, so it is
  built in a narrow form.
- **Each covers a different moment:**
  - C1 acts before an edit (reading context elsewhere).
  - C2 acts while writing code that depends on prose.
  - C3 acts after a change (prose it made false).
  - C6 retires a page of the docs folder.
- **None is a variant of the shipped skill.** The shipped skill governs the comments an
  agent writes. These four govern reading, verifying, finding drift and moving facts.
  Each eval has a `shipped_skill` arm to test that claim. If the shipped skill matches
  a new one, the new one is a #21/#48 finding, not a new skill.

## What the judges asked for, and where it went

| Advice | Where it went |
| --- | --- |
| Run a no-skill derivability gate first, and drop or harden cases both bare models pass | The build workflow's gate and harden stages; each skill's `eval/GATE.md` |
| Keep hidden tests out of `files/` | `eval/hidden/<case>/hidden_tests/`, run by `gradelib.run_hidden_tests` |
| Give reply keyword checks little weight | Graders carry a `focus`; the benchmark reports `reply` separately |
| Add a shipped-skill falsification arm | `shipped_skill` arm in `incubator/harness.py` |
| Do not let `lint_skills.py` miss the new cases | `scripts/lint_skills.py` now includes every incubator skill's cases, references and hidden tests in its copied-text check, so shipped-skill variants cannot copy them either |
| C1: frame in the user's terms; instructions plus a grep recipe first, script later; no file list in prompts; distractors | C1's brief |
| C2: centre on comments and docstrings; drop instruction-file cases (eval agents inherit the real `AGENTS.md`) | C2's brief |
| C3: lead with value drift; keep records word for word; avoid rename-only traps | C3's brief |
| C6: only on an explicit request about one page; grade only what nobody disputes; leave the module-docstring question to the user | C6's brief |
