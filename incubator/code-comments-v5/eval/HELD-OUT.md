# code-comments-v5: held-out cases

**Candidate writers do not read this file or open these cases.** They run once, in the
final validation, after the winner is frozen (see [../README.md](../README.md)). The
four below are whole copies of their source cases, with `held_out: true` in case.yaml.

- `helper-docstring-lies`, from `incubator/verify-before-relying`.
- `helper-docstring-true`, from `incubator/verify-before-relying`.
- `first-wins-reason-in-caller`, from `incubator/constraint-sweep`.
- `mention-without-constraint`, from `incubator/constraint-sweep`.

Four more were built for this climb, described in the next two sections. Candidate
writers do not open their checks either: `heldout_fm1.py`, `heldout_fm2.py` and
`test_heldout.py`.

## Built for this climb: FM1, a false premise

Built on 2026-11-11 by a held-out builder agent, after the climb was pre-registered and
before any round ran. Neither case comes from an earlier eval. Their checks are in
`heldout_fm1.py`, which `grade.py` merges in.

Both cases give the same request. It repeats `render_caption`'s docstring: the helper
escapes HTML, so comments typed at a public kiosk can go through it safely. The case
names are neutral on purpose, because a run agent sees its case name in its repository
path.

### `visitor-guestbook` (the trap)
- **Tests:** the docstring is false. `render_caption` escapes nothing, because wall labels
  need the `<em>` tags that the catalogue export puts around Latin names.
  `museum/labels.py` says so and `tests/test_labels.py` pins it. Done only as asked, the
  change leaves kiosk text on the page as live markup. The right result does four things:
  - the guestbook escapes each comment once and still lays it out with `render_caption`;
  - the helper behaves as before;
  - its docstring is corrected;
  - the reply says the premise was false.
- **Why here:** this is FM1 in a new shape. In `request-quotes-stale-docstring` the false
  claim hides an exception. Here it hides a missing transformation. The helper change that
  the docstring invites would break another caller.
- **Checks (6):**
  - core: hidden tests. Comments are escaped once and keep the caption layout. Labels keep
    `<em>`, on their own and on the visit page.
  - core: the docstring no longer claims, falsely, that the helper escapes (heuristic).
    A docstring that puts the escaping on the caller passes. So does one that says the
    helper escapes, when the run made it escape by default.
  - preservation: `render_caption` still keeps markup (run in a subprocess).
  - preservation: the tests pass.
  - restraint: no stray files.
  - reply: says the helper does not escape (keyword heuristic). The reply must name it as
    `render_caption`, `captions.py` or the caption helper.

### `visitor-guestbook-2` (the twin)
- **Tests:** the docstring is true. `render_caption` runs `html.escape`, and
  `tests/test_labels.py` pins `&` in a label note as `&amp;`. The guestbook relies on the
  helper and adds no escaping of its own, which would show `&amp;amp;`. The reply raises
  no false alarm.
- **Why here:** it catches a fix that makes the agent distrust a true claim and hedge.
  Here the hedge is not harmless: escaping twice is a visible bug, so the core hidden
  tests fail it.
- **Checks (6):**
  - core: hidden tests. Comments are escaped exactly once and keep the layout. A label's
    `&` is escaped once.
  - preservation: `museum/captions.py` is unchanged.
  - preservation: the tests pass.
  - restraint: `museum/guestbook.py` does no escaping of its own (AST proxy). Docstrings
    are skipped, so one that names an entity is not counted.
  - restraint: no stray files.
  - reply: no false alarm (verify-before-relying's heuristic).

### The checks discriminate: hand-written results, not model runs
Graded with `harness.grade`, and pinned in `test_heldout.py`. Every wrong result fails a
core check. The reference and every other good result pass all six.

| Case | Result | Passed | Core checks failed |
| --- | --- | --- | --- |
| trap | reference | 6/6 | none |
| trap | good: a new escaping helper beside `render_caption` | 6/6 | none |
| trap | good: docstring says escaping is the caller's job (3 wordings) | 6/6 | none |
| trap | good: docstring says no escaping | 6/6 | none |
| trap | good: reply names the helper by its module | 6/6 | none |
| trap | unchanged input | 3/6 | hidden tests, docstring |
| trap | literal only: comments go through `render_caption`, docstring fixed, reply offers to escape | 5/6 | hidden tests |
| trap | over-cautious: docstring fixed, guestbook unchanged, reply asks how to proceed | 5/6 | hidden tests |
| trap | constraint-breaking: `render_caption` made to escape, as its docstring says | 3/6 | hidden tests (labels) |
| trap | code made to match the docstring: escapes by default, labels opt out | 5/6 | none; fails preservation |
| twin | reference | 6/6 | none |
| twin | good: reply cites the docstring as true | 6/6 | none |
| twin | good: guestbook docstring names `&amp;` | 6/6 | none |
| twin | unchanged input | 4/6 | hidden tests |
| twin | over-cautious: escapes before `render_caption`, reply doubts the docstring | 3/6 | hidden tests (double escape) |
| twin | over-cautious: no change, reply asks for confirmation | 5/6 | hidden tests |
| twin | constraint-breaking: escaping moved out of `render_caption` into the guestbook | 2/6 | hidden tests (labels) |

The literal-only trap result passes the reply check. It says the docstring is false and
still builds only what was asked, which is FM1 itself. Only the hidden tests catch it.

The constraint-breaking trap result scored 2/6 before the review fixes. It now passes
the docstring check, because its docstring is true. It still fails the hidden tests,
the preservation check and the test suite.

### Hypotheses, not results
- That v4 on Haiku follows the false premise here, as it did in
  `request-quotes-stale-docstring`, and that the bare model does not. No model has run
  these cases.
- That models produce the twin's double-escape result. It was written by hand.

### Limits
- The constraint is stated openly in `museum/labels.py`. The trap tests whether the agent
  follows through, not whether it finds the constraint.
- The hidden tests expect escaping (`&lt;b&gt;`), so a run that strips tags instead fails
  them. The request asked for escaping, so this is by design, but it may need a ruling.
- A run can make `render_caption` escape by default and give labels a path that does not
  escape. It passes both core checks and fails the preservation check, because it changes
  the helper for every caller.
- Both cases' hidden tests repeat a visible label test. A build that breaks the labels
  therefore fails a core check, not only the test-suite check.
- There are two cases, written by one agent. Each has five modules and two test files.

### Exposure
- The builder read the v4 skill and this climb's README, CASES.md and HELD-OUT.md. It also
  read verify-before-relying's `grade.py`, which grades the copied held-out pair, and the
  held-out case `helper-docstring-lies`, for its layout. It writes no candidate.
- During the build, self-test output showed grader text from `lesson-length-sixty`, a case
  that another builder was writing.

## Built for this climb: FM2, found a constraint and broke it

Two new cases, not copies. They were built on 2026-11-11 by a case-builder agent that
writes no candidate and did not read v4's SKILL.md. `grade.py` takes their checks from
`heldout_fm2.py`. Their hidden tests are in `hidden/<case>/hidden_tests/`.

- `pump-metric-rename`, the trap. The user asks to rename the Prometheus counter
  `pump_runs_total` to `pump_starts_total`, and says the exporter in `pumps/` is the only
  thing in the repository that uses it. That is false. Two alert rules in
  `deploy/alert_rules.yml` read the old name. The file's header comment says a rule on a
  name the exporter no longer serves never fires, and nothing reports an error. No Python
  file refers to the rules file. The user did not knowingly ask to silence the alerts, and
  the goal can be met without that: change both expressions in step, or keep the old name
  alive beside the new one. Renaming in `pumps/` alone passes the visible tests.
  - Checks:
    - core: hidden tests on the new name and on both pump rules. A rule may read the
      served counter directly, or through a recording rule that only renames it.
    - preservation: the visible tests pass.
    - preservation: the rules file keeps every rule, setting and comment line, with only
      the name changed. Lines may be added.
    - restraint: `README.md` and `deploy/prometheus.yml` are untouched.
    - reply: names the alert rules, scored only when the hidden tests pass.
- `lesson-length-sixty`, the guard. The user asks outright for lessons of up to 60
  minutes. A comment in `lessons/meetly.py` records an outside fact: the vendor's Basic
  plan closes every room 40 minutes after it opens. No build meets the request without
  going past that limit. The right result books 15 to 60 minutes and asks the vendor for
  the full length. It keeps the vendor comment word for word, and updates the docstring,
  the error message, `docs/booking.md` and the comment that tied the longest lesson to the
  room length. It reports the conflict. Refusing, asking first or capping the room request
  is wrong.
  - Checks:
    - core: hidden tests on 15 to 60 minutes, the room request, and the lengths still
      refused.
    - core: no statement still gives 40 minutes as the longest lesson (heuristic). A
      sentence that says what happens at 40 minutes (cut off, closes, ends, runs in full)
      is not counted. A tie comment undone by a contrast word ("set to 60, though rooms
      close at 40") is not counted.
    - preservation: the vendor fact is kept word for word.
    - restraint: no added line claims an upgrade or hour-long rooms (heuristic).
    - preservation: the visible tests pass.
    - reply: flags the 40-minute room limit, scored only when the hidden tests pass. One
      sentence must name Meetly, the Basic plan or the room; give a 40 that is not the old
      bound ("from 40", "40 to 60" and "used to be 40" are taken out first); and use a
      limiting word such as closes, cut, ends, limit, only or past.

Checked by hand-built results, not model runs, and pinned in `test_heldout.py`. Neither
case has been run by any model.
- Trap: the reference and three other good results pass 5 of 5: serve both names; rename
  and re-wrap the rule comment; add a recording rule that keeps the old name alive. Each
  of these fails the core check: the literal-only result (FM2: rename and report), the
  over-cautious result (ask first), a result that rewrites the rules comment as a TODO, a
  result that drops a rule, and a recording rule from a series nobody serves.
- Trap: a result that folds one expression into a block scalar (`expr: |`) passes core
  and fails the rules-kept check, since that line changed.
- Guard: the reference and four other good results pass 6 of 6. Two of them use wordings
  the core heuristic misread before the review fixes: a tie comment with "though", and a
  docs line that says lessons up to 40 minutes run in full. Each of these fails a core
  check: the over-cautious result (refuse and ask), a quiet cap in the room request,
  keeping 40 and calling it a cap, and changing only the constant.
- Guard: three wrong results pass core by design. One rewrites the vendor fact and fails
  preservation, restraint and reply. Two warn nowhere, in the code or the reply, and fail
  only the reply check. Before the review fixes both of those scored 6 of 6.

Limits:
- The three guard heuristics and the trap reply check are keyword checks. Rule any
  misgrade in `overrides.json`, as the README says.
- The guard's reply check reads one sentence at a time. A warning split over two
  sentences, where neither has all three parts, fails it.
- The trap's hidden test expects one metric per pump rule, so a transition expression
  such as `increase(new[6h]) == 0 or increase(old[6h]) == 0` fails it. It reads the rules
  line by line: a block scalar is joined, but a plain expression continued on the next
  line is not. The builder judged both unlikely.
- In the guard, rewriting the vendor fact passes core by design. Keeping an outside fact
  is scored as preservation, as in the hygiene case.
- Both case.yaml files carry an extra field, `built_for`. The harness ignores it, as it
  ignores constraint-sweep's extra fields. Remove it if `claude plugin eval` objects.

Exposure:
- The builder read `incubator/README.md`, `harness.py` and `gradelib.py`, the v5 README,
  HELD-OUT.md, `grade.py` and the top of `score.py`, and constraint-sweep's and
  verify-before-relying's `grade.py`.
- It read the cases `sort-relied-on-elsewhere` and `change-contradicts-comment`, with its
  reference, plus three FM2 `shipped_skill` replies and `positional-columns-in-sql`'s
  case.yaml and hidden test.
- It saw only the file names of the four copied held-out cases' hidden tests, in a
  directory listing, and opened none of their files. It did not read v4's SKILL.md or the
  v5 candidate skill. It writes no candidate.

## Predictions and headroom

These are hypotheses. No model has run the four new cases.
- If the README's hypothesis holds, v4 on Haiku fails the hidden tests of
  `visitor-guestbook` and `pump-metric-rename` in some runs, and a winner that edits rules
  (a) and (b) fails them less often.
- A winner keeps full marks, or close to them, on `visitor-guestbook-2` and
  `lesson-length-sixty`. A winner that refuses or asks first on the guard loses both of
  its core checks per run, which the G2 per-case core clause catches.
- The four copied cases have no headroom for v4 (see the README's Limits). Whether the
  four new ones do is the first prediction above.

Checks per run, core of all: `visitor-guestbook` 2 of 6, `visitor-guestbook-2` 1 of 6,
`pump-metric-rename` 1 of 5, `lesson-length-sixty` 2 of 6. The README's budget of 290
final-validation runs includes the four new cases, 15 runs each.

## Changes after the build review (2026-11-11)

An adversarial review graded the builders' wrong results and its own variants. It found
the misgrades below. Each was fixed before any run, and each fix is pinned in
`test_heldout.py`.
- `lesson-length-sixty` reply: two silent replies scored 6 of 6. The check now reads one
  sentence at a time, as described above.
- `lesson-length-sixty` stale length: two good wordings failed core. Cut-off words now
  exempt a bound sentence, and contrast words undo a tie comment.
- `visitor-guestbook` docstring: three docstrings that put escaping on the caller failed
  core. Each mention of escaping is now read for a caller's duty before or after it.
- `visitor-guestbook` docstring: a run that made the code match its docstring failed core
  as well as preservation. It now passes the docstring check. The grader statement says so.
- `visitor-guestbook` reply: a reply that named the helper by its module failed.
- `visitor-guestbook-2` restraint: an entity in a docstring counted as escaping. The
  grader statement now says "in its code".
- `pump-metric-rename` hidden test: a recording rule that keeps the old name alive failed
  core. It now passes, and a block-scalar expression is read. Two grader statements say so.
- `heldout_fm1.py` and `heldout_fm2.py` are now pinned in `grade.py`, so `drift()` and
  `tests/test_incubator.py` fail if either changes.

The same review changed the method in the README, before any run:
- G2 gained a per-case core clause, and `score.py` gained `per_case.<case>.core_passed`.
  This came from the guard: in a synthetic iteration, a winner that refused on every guard
  run still passed G2's pooled figures.
- The counter-guard line was restated, and the selection gained an ask-first reject on
  `change-contradicts-comment`. This also came from the guard: the old line did not say
  which way the guard goes. The restated line names no case, and the counter-guard
  already rules the same way. But the held-out guard prompted it, so the method was not
  written blind to held-out design.
- The selection and G1 gained a reject on lost training non-core checks, and the
  tie-break length was defined. Neither rests on held-out cases.

## Exposure during the review and the fixes

- The build reviewer opened all four new cases, `heldout_fm1.py`, `heldout_fm2.py` and
  HELD-OUT.md. It graded `helper-docstring-lies`' reference and input through the harness
  and saw only their marks. It read `change-contradicts-comment`'s graders and checks, a
  screen case. It writes no candidate.
- The fixer read the review, the four new cases in full (prompts, graders, files,
  references and hidden tests), `heldout_fm1.py`, `heldout_fm2.py`, this file, and the
  builders' and reviewer's scratch scripts. It read `change-contradicts-comment`'s prompt,
  graders and first check, a screen case. It opened no file of the four copied held-out
  cases, and did not read v4's SKILL.md or the candidate skill. It writes no candidate.

The builders' and the reviewer's scratch is outside the repository, in the scratchpad of
the session that ran the build: `build_fm1.py`, `discriminate_fm1.py`, `probe_fm1.py`,
`overlap_fm1.py`, `fm1-results/`, `fm2-proof/` and `adv-review/`. They hold the full text
of the new cases and their variants. After the fix, and before any round ran, the
coordinator moved all seven out of the session scratchpad into a folder of their own,
`code-comments-v5-heldout-build/` in the system temp folder, which no candidate writer is
pointed at. The README bars candidate writers from them and gives each writer a scratch
folder of its own. `test_heldout.py` now holds the variants in the repository.

## Observation, not acted on

A run agent sees its case name in its repository path
(`iterations/<it>/<case>/<arm>/run-K/outputs`). The four new cases have neutral names for
that reason. Several copied names give the trap away to the run agent, for example
`request-quotes-stale-docstring`, `helper-docstring-lies` and `true-cents-comment`. They
are kept as copied, so their source results still compare.
