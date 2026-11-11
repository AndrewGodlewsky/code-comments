# constraint-sweep eval cases

Seven cases: five for training and two held out. Each case is a small Python
repository of 11 to 16 files, aimed at one behaviour: before changing what existing
code returns, orders, accepts or removes, read what other files' comments, docstrings
and tests say about it. Keep every constraint that still binds, or report it, and
report any that are stale. The prompts list no files, because the eval measures
whether the agent finds that context. Every fixture also mentions the changed symbol
in places that state nothing binding, so a single grep hit is not enough.

All seven cases were designed before any run existed, and revised on 2026-11-11 after
review, still before any run. The bare-model derivability gate then put four discovery
cases at ceiling, and those four (plus the pointer twin, which mirrors its base case)
were hardened on 2026-11-11. No skill-arm run has happened yet. [GATE.md](GATE.md) holds
the gate results, the one grader fix and what changed in each case. Held-out cases
(`held_out: true` in `case.yaml`) are never used to decide a skill edit.

## Cases

Context columns, from `case.yaml`:
- **other file**: `context_in_other_file`, the full constraint is stated in a file other
  than the one being edited.
- **core needs it**: `core_needs_other_file`, the evidence that rules out the natural
  wrong edit is found only in another file, and nothing in the edited file points to it.
- **pointer**: `pointer_at_edit`, the edited file names the other file and the fact.

| Case | Split | Other file / core needs it / pointer | Behaviour | Trap | Where the needed evidence lives | Heuristic checks |
| --- | --- | --- | --- | --- | --- | --- |
| `sort-relied-on-elsewhere` | train | yes / yes / no | Drop a Python sort the user thinks nobody needs, but keep the id order a non-Python consumer relies on (for example `ORDER BY id`), and say why. | The user names both Python callers, and both really are indifferent to order: `ledger/api.py` sums the rows, and the accounts team re-sorts the export (`docs/accounts-sheet.md`). What needs the order is a shell script nothing imports. Deleting the sort passes the visible tests (they compare ids as sets) and gets the bank upload rejected. Sorting in `nightly.py` or `csv_out.py` instead keeps the file in order but moves the cost into a consumer, and fails restraint. | `ops/nightly.sh` comment: the bank's matcher rejects the upload unless ids ascend, and the file goes up in `fetch_rows` order. A `*.py`-only search for `fetch_rows` misses it; an all-types search finds it. | 06 (reply names `ops/nightly.sh` or the bank; scored only if core passes) |
| `dispatched-by-name` | train | yes / yes / no | Remove dead code, but keep a handler whose name is built at runtime from a config file's event kinds. | No file spells out `handle_chargeback` except its definition and `CHANGELOG.md`, the same search profile as the two dead functions (`handle_refund_v1`, `format_old_receipt`). Keeping every `handle_` function keeps the dead `handle_refund_v1`. | `events/dispatch.py` (`getattr(handlers, "handle_" + kind)`) and `config/routes.ini` (lists `chargeback = on`; its comment says each kind is served by `handle_<kind>` and removing one breaks that kind). | 06 (reply says why `handle_chargeback` stayed; scored only if it is still defined) |
| `positional-columns-in-sql` | train | yes / yes / no | Add a column the user wants next to `amount`, without breaking a positional SQL consumer. | The user says finance reads columns by header, so the order is free. `docs/finance.md` and `reports/monthly.py` (`csv.DictReader`, with a comment that order does not matter there) agree. Inserting next to amount and touching nothing else passes the visible tests and loads currency codes into `posted_at`. No Python file refers to the SQL. | `deploy/warehouse/load_ledger.sql` comment (fields by position; new columns at the end of `COLUMNS` in `exporter/csv_out.py`) and its `SELECT c1, c2, c3, c4`; `deploy/warehouse/schema.sql`. | 04 (when load_ledger.sql's SQL changed: its comments still say "position" and name COLUMNS or csv_out); 06 (reply mentions the load; scored only if core passes) |
| `positional-columns-in-sql-pointer` | train | yes / no / yes | Control. The point-of-edit twin of `positional-columns-in-sql`: the same repository, request, graders and hidden tests, plus one comment above `COLUMNS`: "deploy/warehouse/load_ledger.sql reads these fields by position." | As in its twin, but the edited file now points at the SQL. This is ADR 0001's pointer mitigation, on the same task. Expected to be easier; it may sit near ceiling by design. | The pointer in `exporter/csv_out.py`, then `deploy/warehouse/load_ledger.sql`. | as its twin |
| `stale-constraint-elsewhere` | train | yes / no / no | Restraint. A comment elsewhere states a constraint that its own code no longer relies on. Make the change, add no sort to a consumer, and fix or report the stale comment. | The user only asks for the sort to go, with no view on the consumers. An agent that obeys the stale comment refuses, keeps the sort, or moves it into a consumer. A bare edit removes the sort and leaves the false claim unmentioned. | `metrics/rollup.py`: the comment claims it relies on `load_readings`, while the line below sorts; `alerts/spikes.py` sorts too; `tests/test_rollup.py::test_rollup_accepts_readings_in_any_order`. | 05 (claim gone from rollup.py's prose, by a sentence regex; or a reply sentence calls the rollup comment stale, by keyword) |
| `mention-without-constraint` | held out | no / no / no | Restraint. Add a `currency` argument to `round_price`. Other files mention `round_price` only descriptively, and every statement there stays true, so no file other than `pricing/rounding.py` changes and the reply does not ask about callers. | An agent that treats every mention as a constraint edits a caller, adds defensive code, or stops to ask about callers. | None needed: the four mentions (`pricing/tax.py`, `invoices/lines.py`, `shop/labels.py`, `shop/reports.py`) state nothing the change affects. | 05 (no question about callers or mentioning files) |
| `first-wins-reason-in-caller` | held out | yes / yes / no | Simplify a clunky loop and keep which duplicate wins, whose reason is stated only in a downstream consumer. | The user says it does not matter which login is kept and suggests copying `last_devices`, a last-wins dict comprehension in `accounts/devices.py`. The clunky loop keeps the first event by walking the events in reverse and overwriting, under a variable named `latest_seen`. Both Python callers are indifferent: `reports/weekly.py` says any event will do, and `accounts/export.py` just writes the result to the `user_logins` table. The visible tests check only one event per user. | `billing/trial_clock.sql` comment: the `user_logins` row from `one_login_per_user` must be the user's first login, the activation date that starts the 14-day trial clock. No Python file reads it. | none |

The case name `first-wins-reason-in-caller` is kept from before the gate so the gate
record stays traceable; the "caller" is now the billing SQL view that reads the table
the function's result is written to.

**The positional pair has a preferred result and an accepted one.** Preferred: currency
goes next to amount and `load_ledger.sql` is changed in step (for example
`SELECT c1, c2, c3, c5`), and the reply says so. That is the reference. Accepted:
currency goes at the end and the reply says why it is not next to amount. Both pass
every check; a bare model that puts it at the end is not penalised. Adding the column
to the warehouse through a new migration file in `deploy/warehouse/` also passes: the
hidden load runs `schema.sql`, then every other `deploy/warehouse/*.sql` except
`load_ledger.sql` in name order (including `retention.sql`, which deletes from an empty
table), then `load_ledger.sql`.

**The order of `one_login_per_user`'s result is not graded.** Nothing in the repository
depends on it, so the hidden test checks which event each user keeps, and the trial
clock the billing view computes from them, not their order.

## Checks

Each grader file holds one statement, and `grade.py` has one check per file, in the
same order. Focus values:

- **core**: hidden tests in `hidden/<case>/hidden_tests/`, run by
  `gradelib.run_hidden_tests` on a copy of the run. The agent never sees them. They
  test the consumer, not the edited function alone: the export file's id order (what
  the bank upload needs), routed dispatch through the real routes file, the warehouse
  load run from the repository's own SQL, the file-order rollup, CHF rounding with
  callers unchanged (called with `currency=` by keyword, so a keyword-only argument
  passes), and first-wins plus the billing view's trial clock.
- **restraint**: the request was done, not refused (the Python sort is gone, the dead
  functions are removed, the currency column exists, `one_login_per_user` was
  rewritten). Every case except `stale-constraint-elsewhere` also checks that **files
  the run only read are byte-identical**: every file except the edited one, the files
  the case allows to change, and `tests/`. Allowed: `ops/nightly.sh` (sort; its own
  preservation check keeps its commands and comment lines, and allows an added
  pointer), `config/routes.ini` (dispatched; its own check requires it unchanged),
  `deploy/warehouse/` (positional pair) and `billing/trial_clock.sql` (first-wins; its
  own check keeps its SQL and comment lines, and allows an added pointer). The stale
  case instead keeps every accurate comment line in every file and the code of every
  consumer. Restraint also counts added comment lines and catches a guarantee moved
  into a consumer. A skill that makes agents over-cautious loses here.
- **Comment counts are net.** "At most three comment or docstring lines are added"
  counts, per file, the comment and docstring lines added minus those removed, never
  below zero, over Python, shell and SQL files outside `tests/`. A reworded or
  re-wrapped line replaces a line; it is not an extra one. This is the gate's one
  grader fix (see GATE.md).
- **preservation**: the repository's own tests pass, and the files that hold the
  constraint keep their code and comments (`ops/nightly.sh`, `routes.ini`, the SQL
  comments, `billing/trial_clock.sql`, accurate comments in the stale case).
- **reply**: keyword checks on `RESPONSE.md`. Their evidence starts with "(heuristic)".
  They never decide a case alone. Where a reply check's statement describes an outcome
  (the export is in id order, the load still maps, handle_chargeback is still defined),
  it is scored only when that outcome happened, so a reply that names the right file
  cannot pass a run that broke it. Record any ruling in `overrides.json`.

The grader frontmatter keeps `weight` (2 for core, 1 otherwise) for the layout that
`claude plugin eval` reads. `incubator/harness.py` ignores it: its headline pass rate is
the unweighted share of checks passed. **Read core and restraint as the headline**, and
reply as a separate column, which `benchmark.md` already reports per focus.

All other checks are AST, byte-identity, code-shape, command-line, SQL-text, counting or
hidden-test checks. The twin's hidden check first confirms that the twin still matches
its base case in everything but `exporter/csv_out.py` (prompt, graders, fixture, hidden
tests), and fails with the drifted paths if not.

`case.yaml` adds four fields beyond the hygiene layout: `context_in_other_file`,
`core_needs_other_file`, `pointer_at_edit` and `evidence_in` (the files that hold the
needed evidence). The twin also has `twin_of`.

## Answering ADR 0001's revisit question

ADR 0001 asks whether readers miss context that lives in other files and whether
search, or a pointer, without an index, fixes it.

- **Did the agent find the file?** `eval/discovery.py` reads the agent transcripts and
  reports, per run and per `evidence_in` file, whether the agent read it or saw it in a
  search result before its first edit. That separates "never found it" from "found it
  and ignored it". It reads the transcripts each time and stores nothing. Tested on
  synthetic transcripts only so far.
- **Do readers miss it?** Read the bare (`without_skill`) arm's discovery rate and core
  pass rate on the cases where `core_needs_other_file` is true: `sort-relied-on-elsewhere`,
  `dispatched-by-name`, `positional-columns-in-sql` and `first-wins-reason-in-caller`.
  In `stale-constraint-elsewhere` the other-file context matters only for check 05.
- **Does a pointer fix it?** Compare `positional-columns-in-sql` with its twin
  `positional-columns-in-sql-pointer`. They differ only in one comment in the edited
  file, so the difference in pass rates measures the pointer, not the task.
- **Does search fix it?** Compare the `with_skill` and `reminder` arms against the bare
  arm on the cases where `core_needs_other_file` is true. The `shipped_skill` arm shows
  whether the hygiene skill's one search line already does this. In
  `dispatched-by-name` a search for the full changed name finds nothing, so it also
  shows whether an arm handles names built at runtime.
- With two to five runs per arm, these are directions to check, not measured effects.

## Headroom (hypotheses, not results)

The first gate (GATE.md) found the original fixtures too easy: on every discovery case
the bare models found the other file and kept the constraint in all three runs. Each
original fixture tied the evidence to the edited symbol through a Python importer, a
config value that spelled out the full name, or a README line that pointed at the SQL,
in an 11- or 12-file repository a model reads end to end. The hardened fixtures remove
that link, keep the evidence where a repository-wide search for the changed name (or,
for the runtime-built name, its stem) finds it, and add a reader of the same output that
genuinely does not care.

- `sort-relied-on-elsewhere`: the user names both Python callers, and reading them
  confirms the user's belief. Only the shell script disagrees.
- `dispatched-by-name`: a search for `handle_chargeback` returns exactly what it returns
  for the dead functions. A model that reads `dispatch.py` sees the runtime name.
- `positional-columns-in-sql`: the request, the docs and a Python reader all say order
  is free; the positional load sits in `deploy/warehouse/`.
- `first-wins-reason-in-caller`: the user proposes the wrong one-liner, and both Python
  callers are indifferent.
- The two restraint cases (`stale-constraint-elsewhere`, `mention-without-constraint`)
  and the pointer twin are expected near ceiling for bare models on core and restraint,
  by design. The restraint cases exist to catch a skill that makes agents obey stale
  comments, edit callers or ask instead of acting.

These are design arguments. **Re-run the bare gate on the four hardened cases and the
twin before any skill run**, and harden again or drop any case both bare models still
pass every time.

## Gaps the cases do not cover

- **Hidden directories.** No fixture has a dot-directory, so the skill's rule about
  searching hidden folders is never exercised. A reserve case could put the binding
  mention in `.github/workflows/`.
- **Reliance that only the code shows.** Every live constraint in the fixtures is
  stated in prose, so the skill's rule that demonstrable reliance binds without a
  comment is untested.
- **Reserve.** `mirrored-column-order`, the earlier point-of-edit control with a
  different task, is kept in `eval/reserve/` and is not run (see its README).

## Verification

Run on 2026-11-11, after the gate hardening:

- `python incubator/harness.py self-test constraint-sweep` prints `self-test ok`: every
  reference passes every check, and every unchanged input fails at least one.
- `python incubator/harness.py lint constraint-sweep` prints `lint ok`, and so do the
  other incubator skills that have a `SKILL.md`.
- Each fixture's own tests pass on `files/` and on the reference.
- Hand-made variants were graded in a scratch folder (not kept). Each failed exactly the
  checks it should:
  - **Traps:** dropping the sort, deleting all three uncalled handlers, inserting
    currency next to amount with nothing else changed (with or without the pointer), and
    a last-wins dict comprehension each fail core. Their reply checks are not scored.
  - **Restraint:** refusing (sort and first-wins), keeping `sorted()` in `rows.py`,
    sorting in `nightly.py`, keeping every `handle_` function, a pointer in
    `dispatch.py`, editing `reports/monthly.py`, `docs/finance.md` or
    `reports/weekly.py`, and five net new comment lines each fail their restraint
    check. Rewording the comment in `ops/nightly.sh`, `routes.ini` or
    `billing/trial_clock.sql`, and a renumbered load whose comments drop the
    by-position fact, fail preservation.
  - **Accepted alternatives:** currency at the end with a reply, a new warehouse
    migration with the load renumbered, a first-wins `reversed` dict comprehension,
    first-wins with no comment, a pointer added to `trial_clock.sql`, and the Sonnet
    gate run's shape (`ORDER BY id` with a four-line docstring that rewords the first
    line) each pass every check.
- Regrading the gate runs of the two unchanged cases on scratch copies gives the same
  results as recorded. The net count turns the Sonnet sort run's check 05 from 4 added
  lines (fail) to 3 net (pass), against its original `rows.py`.
- No 8-word run of case or reference text appears in any existing `SKILL.md`, which is
  the repository linter's leak rule.
