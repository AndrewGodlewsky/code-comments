# Derivability gate, 2026-11-11

The gate runs every case with **no skill** (`without_skill` arm) to find cases a bare
model already gets right, which cannot show a gain. It ran Haiku twice and Sonnet once
on all seven cases. The records are in `iterations/gate-haiku/` and
`iterations/gate-sonnet/`, graded with the fixtures and checks as they were then; they
were not regraded in place.

**Gate runs are for case selection only.** They will not be reused as evaluation runs,
and they decide no skill edit. Running the bare arm on the two held-out cases spends
neither: nothing about the skill was tuned on them, and no skill-arm result exists yet.

## Results per case

Checks passed per run. "Core every run" is whether every core check passed in all three
runs.

| Case | Split | Haiku 1, 2 | Sonnet | Core every run | Decision |
| --- | --- | --- | --- | --- | --- |
| `dispatched-by-name` | train | 6/6, 6/6 | 6/6 | yes | hardened |
| `first-wins-reason-in-caller` | held out | 6/6, 6/6 | 6/6 | yes | hardened |
| `mention-without-constraint` | held out | 3/5, 5/5 | 5/5 | no (an empty run, below) | kept: restraint control |
| `positional-columns-in-sql` | train | 7/7, 7/7 | 7/7 | yes | hardened |
| `positional-columns-in-sql-pointer` | train | 7/7, 7/7 | 7/7 | yes | mirrors its hardened base; a control |
| `sort-relied-on-elsewhere` | train | 6/7, 6/7 | 6/7 | yes | hardened, and one grader fixed |
| `stale-constraint-elsewhere` | train | 5/5, 5/5 | 5/5 | yes | kept: restraint case |

What the runs did, from their `changes.diff` and `RESPONSE.md`:
- **Every discovery case was found.** All three runs of `sort-relied-on-elsewhere` named
  the merge join in `reconcile.py`. All three `dispatched-by-name` runs kept
  `handle_chargeback`, citing `routes.ini` and the runtime lookup in `dispatch.py`. All
  three positional runs read `warehouse/load.sql` and appended currency at the end. In
  the twin, two runs did the same and Haiku's second run put currency next to amount
  and renumbered `load.sql` in step, the preferred result. All three first-wins runs
  cited `accounts/activation.py` and kept the first login.
- **Stale comment fixed without help.** All three `stale-constraint-elsewhere` runs
  removed the sort and rewrote the stale comment in `metrics/rollup.py`. CASES.md had
  predicted that bare runs would fail check 05; none did.

## Failed checks and rulings

1. **`mention-without-constraint`, Haiku run 1, checks 01 (core) and 05 (reply).** The
   run left the repository byte-identical to `files/` and wrote no `RESPONSE.md`. It is
   an empty run: the agent stopped before doing anything. **Not a grader bug.**
   `round_price` still has no `currency` argument, so the hidden test's error is right,
   and a missing reply cannot pass a reply check. It shows no headroom: the case's
   other two runs passed every check.
2. **`sort-relied-on-elsewhere`, Haiku runs 1 and 2, check 02 (restraint, "no longer
   sorts in Python").** Both runs found the merge join, changed nothing, and offered
   `ORDER BY id` as option 1 of 2 or 3. **Not a grader bug.** The user asked for the
   Python sort to go, and both replies named a safe way to do that without doing it.
   That is the over-caution check 02 exists for. Kept as it was.
3. **`sort-relied-on-elsewhere`, Sonnet run 1, check 05 (restraint, "at most three
   comment or docstring lines are added").** The run did what the reference does:
   `ORDER BY id`, no Python sort, and a docstring giving the order contract and its
   reason. The check counted 4 added lines, but one was the existing one-line
   docstring reworded ("Return the ledger rows." became "Return the ledger rows,
   ordered by id."), so 3 lines were new. **Grader bug, fixed.** The count is now net
   per file: lines added minus lines removed, never below zero, so a reworded or
   re-wrapped line counts as a replacement. It now covers shell and SQL comments too,
   because two hardened cases allow a pointer in a `.sh` or `.sql` file. Against a copy
   of that run with its original `rows.py`, the old count gives 4 (fail) and the new
   one 3 (pass). Regrading the gate runs of the two unchanged cases on scratch copies
   gives the results as recorded. The same count serves `mention-without-constraint`,
   `first-wins-reason-in-caller` and the positional `csv_out.py` limit, and their
   statements now say "counted net". This does not let a bad result pass: more than
   three new lines still fails, and rewording a comment in any other file is caught by
   the preservation and byte-identity checks.

## Cases kept at ceiling

- **`stale-constraint-elsewhere`** is a deliberate restraint case. It catches a skill
  that makes agents obey a stale comment: refuse, keep the sort, or move it into a
  consumer. Bare models at ceiling here is the expected result. Check 05 showed no
  bare-model headroom, so a skill cannot gain on it, only lose.
- **`mention-without-constraint`** (held out) is a restraint control: descriptive
  mentions must trigger no edits, defences or questions. Its one failure was the
  empty run above.
- **`positional-columns-in-sql-pointer`** is a control: the pointer at the point of edit
  is ADR 0001's mitigation, so this twin is meant to be easier than its base. It must
  match its base case in everything but `exporter/csv_out.py`, so it was rebuilt with
  the hardened base. The twin check in `grade.py` confirms that they match.

## How each ceiling case was hardened

Each original fixture tied the evidence to the edited symbol in a way a bare model
follows: a Python importer that names the symbol, a config value that spells out the
full name, or a README line that points straight at the SQL. And each was an 11- or
12-file repository a model can read end to end. Hardening removes that link while
keeping all the needed evidence in the repository, where a search for the changed name
across every file type finds it. It also adds a reader of the same output that genuinely
does not care, which supports the user's mistaken belief. Requests stay realistic, and
none mentions the skill, comments or the trap.

### `sort-relied-on-elsewhere` (train)

- **Was easy because** `nightly.py` passed `fetch_rows` straight into `reconcile`, and
  `reconcile.py`'s comment named `fetch_rows`, so following Python callers reached it.
- **Now:** no Python code needs the order. The user names the two Python callers, the
  nightly export and the balances API, and both really are indifferent: `api.py` sums
  the rows, and `docs/accounts-sheet.md` says the accounts team re-sorts the sheet.
  The reliance is in `ops/nightly.sh`, which cron runs (`ops/crontab`). It uploads the
  export to the bank's matching service exactly as written, and its comment says the
  bank rejects the file unless ids ascend, so it relies on `fetch_rows` sorting by id.
  The repository has 16 files.
- **Natural wrong edit:** check the two callers the user named, find they agree, delete
  the sort line. The visible tests compare ids as sets and pass.
- **Search probe:** `grep -rlw fetch_rows` over every file lists `ops/nightly.sh`; the
  same search limited to `*.py` does not.
- **Checks:** core is a hidden test that the export file lists out-of-order entries in
  ascending id order. 04 keeps `nightly.sh`'s commands and comment lines. 06's reply
  keywords are now `nightly.sh` or `bank`. 07 allows `ledger/rows.py` and
  `ops/nightly.sh` to change.

### `dispatched-by-name` (train)

- **Was easy because** `config/routes.ini` spelled out `chargeback = handle_chargeback`,
  so a search for the name found the route.
- **Now:** `routes.ini` lists event kinds only (`chargeback = on`), and
  `events/dispatch.py` calls `getattr(handlers, "handle_" + kind)`. The INI comment says
  each listed kind is served by `handle_<kind>` and removing one breaks that kind. The
  old `_legacy_refund_v1` is now `handle_refund_v1`, a dead handler whose `refund_v1`
  kind the changelog says is no longer accepted, and CHANGELOG.md also mentions
  `handle_chargeback`.
- **Natural wrong edit:** search each function name. `handle_chargeback`,
  `handle_refund_v1` and `format_old_receipt` each turn up only in their own
  definition and the changelog, so delete all three. The visible tests do not
  dispatch a chargeback.
- **Opposite failure:** keep every `handle_` function because dispatch is dynamic. That
  keeps the dead `handle_refund_v1` and fails check 02.
- **Search probe:** `grep -rlw handle_chargeback` lists only `CHANGELOG.md` and
  `events/handlers.py`; `grep -rlw chargeback` adds `config/routes.ini`.
- This case now exercises names built at runtime, a gap CASES.md listed.

### `positional-columns-in-sql` (train) and its pointer twin

- **Was easy because** the README said "`warehouse/`: SQL run on the warehouse side",
  and the 11-file repository was read in full.
- **Now:** the load is `deploy/warehouse/load_ledger.sql`, beside `schema.sql` and a
  `retention.sql`, and the README says only "`deploy/`: production cron entries and the
  jobs they run". A new Python reader, `reports/monthly.py`, reads the nightly files
  with `csv.DictReader` under a comment saying column order does not matter there. The
  request adds the user's belief: "They find columns by header name, so the order is up
  to us." The repository has 16 files. The twin's pointer now names
  `deploy/warehouse/load_ledger.sql`.
- **Natural wrong edit:** check the readers the Python code shows (the docs and
  `monthly.py` both say order is free) and insert currency after amount.
- **Search probe:** `grep -rlw COLUMNS` lists `deploy/warehouse/load_ledger.sql` and
  `exporter/csv_out.py`; limited to `*.py` it lists only `csv_out.py`.
- **Checks:** unchanged in kind, with paths moved to `deploy/warehouse/`. The hidden
  load runs `schema.sql`, any other warehouse script in name order, then
  `load_ledger.sql`.

### `first-wins-reason-in-caller` (held out)

- **Was easy because** `accounts/activation.py` imported `one_login_per_user`, and its
  comment named the function and said the first login is the activation date.
- **Now:** `activation.py` is gone. `accounts/export.py` writes the function's result
  to the `user_logins` table, rebuilding it from the full login history. The reason
  lives in `billing/trial_clock.sql`, the view billing runs on that table: the row
  must be the user's first login, because it starts the 14-day trial clock and a later
  login must never move it. No Python file reads that SQL. The request adds the user's
  suggestion: "a one-liner like last_devices in accounts/devices.py would be fine".
  The repository has 15 files.
- **Natural wrong edit:** copy the suggested `last_devices` comprehension, which keeps
  the last login. The visible tests check only one event per user and pass, while every
  returning user's trial end moves.
- **Search probe:** `grep -rlw one_login_per_user` lists `billing/trial_clock.sql`;
  limited to `*.py` it does not.
- **Checks:** core runs the export and the billing view on an in-memory database and
  checks each trial starts at the first login. 04 keeps `trial_clock.sql`'s SQL and
  comment lines. 06 allows `accounts/events.py` and `billing/trial_clock.sql` to change.
- The case keeps its name so this record stays traceable; its "caller" is now the
  billing view.

## The reminder arm

`arms.json` is unchanged. Its sentence asks for a search of every file type for the
changed names. That finds the evidence in the hardened sort, positional and first-wins
cases, so it stays a real competitor there. In `dispatched-by-name` a search for the
full name finds nothing, so that case also shows whether an arm handles a name built at
runtime.

## Before any skill run

- **Re-run the bare gate** on the four hardened cases and the twin (Haiku x3, Sonnet x2,
  as the README plans). Harden again, or drop, any case that both bare models still
  pass every time, and record it here. The hardening is a design argument, not a
  measured result.
- **Outside `eval/`:** the case table in `../README.md` still describes the old
  fixtures for `dispatched-by-name` ("a function a config file names as a string") and
  `first-wins-reason-in-caller` ("a rule stated only in a caller"). The table in
  `../research.md` does too.

## Verification

Run on 2026-11-11, after these changes: `python incubator/harness.py self-test
constraint-sweep` printed `self-test ok`, and `python incubator/harness.py lint
constraint-sweep` printed `lint ok`. Each fixture's own tests pass on `files/` and on
the reference. The hand-made variants are listed in CASES.md under Verification.
