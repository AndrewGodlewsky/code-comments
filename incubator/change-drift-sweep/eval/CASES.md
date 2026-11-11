# change-drift-sweep eval cases

Seven cases: five for training and two held out. All seven were designed before any run
existed. Each case is a small Python repository with unittest tests, aimed at one
behaviour. The behaviour is what happens after a change re-values, renames or moves
something:
- the prose that states the old value is found, including number words, unit
  conversions and derived figures;
- the living descriptions of the code are corrected, to the right new figure;
- records and outside facts are left word for word.

The candidate is C3 in
[the ideation record](../../ideation/2026-11-11-candidates.json), and the coordinator's
direction for issue #50 overrides it where they differ. C7, review mode for a finished
diff, is out of scope for v1.

**Held-out cases are described only in [HELD-OUT.md](HELD-OUT.md).** Whoever writes or
edits the skill reads this file but not that one. They do not open `cases/`,
`references/`, `hidden/` or `test_grade.py`, which holds held-out variants. A held-out
case is never used to decide a skill edit (see [the incubator rules](../../README.md)).

| Case | Held out | Behaviour | Trap | Where the needed evidence lives | Heuristic checks |
| --- | --- | --- | --- | --- | --- |
| `default-value-drift` | no | Find a changed default stated in digits and as a number word, in a module that never names the constant. Keep records and an outside limit. | `PAGE_SIZE` 50 to 200. A search for `50` or `PAGE_SIZE` misses "fifty at a time" in the `exporter/sync.py` docstring. The same search hits the dated load-test report, a released CHANGELOG entry, and `500` in the ledger team's limit, so a search-and-replace damages all three. | `exporter/config.py` (the value), `exporter/sync.py` (number word), `exporter/client.py` and `docs/api.md` (digits), `docs/reports/2026-03-14-load-test.md` (dated record), `CHANGELOG.md` (released entries), `docs/limits.md` ("set by the ledger team") | 02 (sentence regex and new-figure check), 03 (sentence regex) |
| `unit-spelled-ttl` | no | Find a value that prose states only in another unit, in words, or offset by another setting. Leave the same figure where it describes something else. | `SESSION_TTL_S` 900 to 1800. No prose says 900. The old value appears as "fifteen minutes" in two docstrings (one in `auth/views.py`, which never names the setting) and as "15 min" in `docs/security.md`. Two statements contain neither 15 nor fifteen: "a quarter of an hour" in the `auth/forms.py` docstring, and the "Still there?" banner "after 14 minutes" in `docs/console.md`, which is the timeout less `IDLE_WARNING_S` and must become 29. Three true statements share the figure but describe other things: password-reset links, which have their own 900-second setting; 15 failed sign-ins; and the identity provider's 15-minute tokens. A blanket replace rewrites all three. | `auth/settings.py` (the session TTL, the banner lead and the reset-link TTL side by side), `auth/sessions.py`, `auth/views.py`, `auth/forms.py`, `auth/reset.py`, `auth/lockout.py`, `docs/security.md` ("The identity team sets that lifetime, not this service"), `docs/console.md` | 02 (sentence regex and new-figure check), 03 (sentence regex) |
| `derived-backoff-total` | no | Recompute figures derived from the old value, not only the value itself. | `MAX_ATTEMPTS` 4 to 6. The changed waits list "1, 2 and 4" also needs 8 and 16. Two derived totals never state the attempt count: the 7-second drop time in a comment and "about seven seconds" in `docs/oncall.md`. A product in the docs, 200 POSTs (50 alerts times 4 attempts), must become 300. Two more contain no 4, four, 7 or seven: the gateway-maintenance runbook says the sender "retries each alert three times" (attempts less one, now five), and the `alerts/worker.py` docstring says a backlog of 40 alerts clears "in under five minutes" (40 times about 7 s; now about 21 minutes). A broad replace of "7" also hits the unrelated 7-day outbox retention. This is the miss recorded for Sonnet without the skill in hygiene `retry-cap-elsewhere`, made harder because the doc figures never name the count. | `alerts/config.py` (`BASE_DELAY_S` doubling comment, retention), `alerts/sender.py` (loop and comment), `alerts/worker.py` (one alert at a time), `docs/oncall.md` ("every alert uses all its attempts"), `docs/runbooks/gateway-maintenance.md` | 02 (regex), 03 (figure consistency), 04 (regex) |
| `flag-rename-records-stay` | no | Correct the living docs after a CLI flag rename, including a claim the rename makes false once it no longer names the old flag, and keep the records byte-identical. | `--since` to `--after`, same behaviour. `docs/cli.md` says the option "shares its name and meaning with the API's filter"; the same page shows the orders API's filter is `since`, so a mechanical replace leaves a false claim that spells `--after`. The API's `since=` query is an outside fact that a replace of "since" damages. A search for `--since` also hits the 1.2.0 CHANGELOG entry ("Added `--since`"), ADR 0002 and a dated incident report whose command is what was run that day; all three are records. A run that follows "fix every doc your change made false" literally rewrites them. A fenced README example and a runbook step also need the change. | `app/cli.py`, `app/backfill.py`, `README.md` (fenced example), `docs/cli.md` (the API query and the name claim), `docs/runbooks/backfill.md`, `docs/incidents/2026-07-14-missed-night.md`, `CHANGELOG.md` (Keep a Changelog format with an `[Unreleased]` section), `docs/adr/README.md` ("Accepted ADRs are not edited") | 02 (name-claim regex; the rest are token, line-order and byte checks) |
| `pre-existing-drift-reported` | no | Report drift the change did not cause, and fix the drift it did. | `BATCH_SIZE` 100 to 250. The line after the batch-size sentence in `docs/notifications.md` gives a 60-second flush, but `FLUSH_INTERVAL_S` is 30. That mismatch predates the change. Leaving the line, or correcting only its figure toward the code, both pass; the reply must report the mismatch either way. Rewriting the line, or changing the setting to match the doc, fails. "a hundred at a time" in `README.md` is the number-word miss. Two figures worked out from the size contain no 100: a burst of 1,000 costs "10 calls" in `docs/billing.md` (now 4), and 20 calls a second carry "2,000 notifications a second" in the `notify/sender.py` docstring (now 5,000). | `notify/config.py` (both settings), `notify/batcher.py`, `notify/sender.py`, `README.md`, `docs/notifications.md` (the provider's 500-per-call limit and 20 calls a second as outside facts), `docs/billing.md` | 02 (sentence regex and new-figure check), 03 (sentence pattern), 05 (reply cues) |
| `pointer-comment-needs-nothing` | **yes** | See HELD-OUT.md. | | | |
| `poll-interval-average-wait` | **yes** | See HELD-OUT.md. | | | |

## How each case is graded

Check numbers match the grader files (`graders/NN-*.md`) and the order of `CHECKS` in
`grade.py`. Each case has:
- **Core:** check 01 runs hidden tests from `hidden/<case>/hidden_tests/`. They check that
  the requested change works and that neighbouring settings with the same number are
  untouched, for example `RESET_LINK_TTL_S`, `MAX_TRIES` and `FLUSH_INTERVAL_S`. The last
  check runs the fixture's own tests. The checks in between read the prose: the old value
  must be gone, and every new figure must be right (below).
- **Preservation and restraint:** byte-identity for records and outside facts, a
  line-order check on CHANGELOG.md, and `lost_prose` for every other accurate line. The
  CHANGELOG check leaves released sections untouched, rejects a new release heading, and
  where the file has an `[Unreleased]` heading, accepts new lines only under it. A line
  owned by a more specific check is excluded from the general one, so one mistake is not
  counted twice there. In `flag-rename-records-stay`, check 06 reads each line with
  `--since` replaced by `--after`, and a line that kept `--since` is left to check 02.
- **Reply:** one check, in `pre-existing-drift-reported`. It never carries a case on its
  own.

**Core checks may count one missed doc twice:** once as an old value left (02) and once as
a doc without the new value (03 or 04). This is by design, since both are core failures,
and `test_grade.py` pins it (`bad-headline-only`).

**A wrong new figure fails as surely as a stale old one.** Check 02 of
`default-value-drift`, `unit-spelled-ttl` and `pre-existing-drift-reported` reads every
changed or added sentence about the subject, outside the records. Every figure it gives
for the changed quantity must fit the new value:
- page size: 200 (`200 rows`, `two hundred at a time`, `pages of 200`). A 500 that the words
  around it mark as the ledger's limit (`500-row limit`, `up to 500`) is not a page size;
- idle timeout: 1800 seconds in any unit (`30 min`, `thirty minutes`, `half an hour`). A
  sentence about the banner may also give 29 minutes and the minute before the end;
- batch size: 250 (`250 at a time`, `batches of up to 250`, `two hundred and fifty`), plus
  4 calls for a 1,000-notification burst and 5,000 notifications a second.

Numbers are read in digits or in words up to 999, with an optional hyphen before the unit
(`10-minute`). Naming the constant instead (`PAGE_SIZE rows`) passes.

`derived-backoff-total` check 03 reads every changed or added prose line. Each figure in
those lines must fit six attempts, written in digits, words or as a hyphenated adjective:
- waits and totals in seconds: 1, 2, 4, 8, 16 or 31, with 30 accepted after "about";
- the 40-alert backlog: 1240 s, about 20 or 21 minutes, or an upper bound ("under") from
  21 minutes to half an hour;
- attempts: 6;
- retries: 5 ("5 retries", "retries each alert five times");
- POSTs: 300, or 6 per alert.

Its check 02 also fails history narration that restates an old figure ("previously 7",
"was four", "from 200").

`pre-existing-drift-reported`:
- **Check 03** passes in two cases:
  - the flush sentence is unchanged;
  - it was corrected toward the code with every other word kept. The flush figure may become
    30 seconds, thirty seconds, half a minute or `FLUSH_INTERVAL_S`. "a minute" may become
    "half a minute" or 30 seconds.
- **Check 05** needs one paragraph of the reply that has all four cues:
  - the flush;
  - the doc's figure (60, sixty, or a minute but not half a minute);
  - the code's figure (30, thirty, half a minute or `FLUSH_INTERVAL_S`);
  - a contrast or question ("but", "while", "mismatch", "differs", "which ... ?" and the like).

The heuristic checks read prose by sentence. A Python comment block or docstring
paragraph, or a Markdown paragraph, list item or table row, is split at `.`, `!` and `?`.
A check fails when one sentence holds both a subject word (page, session, batch, ...) and
the old value. The evidence of every heuristic check starts with "heuristic:". When one
misgrades a run, record a ruling in that run's `overrides.json`.

Known misgrade, left as a heuristic: in `unit-spelled-ttl`, a true added sentence that
names sessions and gives 15 minutes for something else ("Unlike sessions, reset links
still expire after 15 minutes.") fails check 02. Record a ruling if a run writes one.

## Headroom: where a bare model is expected to fail

- **Prompts:** these read as a user would write them and, unlike the hygiene eval's,
  list no input files. The rigour judge noted that listing every file meant cross-file
  discovery was never measured. Each repository has 9 to 13 files, so the evidence is a
  `Glob` away.
- **The obvious edit is not enough.** Unlike `retry-cap-elsewhere`, a search for the old
  literal does not finish the job. Number words (`fifty`, `fifteen`, `a hundred`), unit
  conversions (900 s written as 15 min) and derived figures (7 s, 200 POSTs) have to be
  found by reading or by computing the old derived value and searching for it.
- **After the gate, some forms share no digit or word with the old value.** In the first
  version every statement to fix held the old number or its word, or sat beside one, and
  six of the seven cases sat at ceiling ([GATE.md](GATE.md)). Each hardened training
  case now has at least one statement that such a search misses: "a quarter of an hour",
  a banner time offset by another setting, a retry count one less than the attempts, a
  backlog time in minutes, a cost and a throughput worked out from the batch size, and a
  claim about the flag's name that stays false after a mechanical rename.
- **Over-editing is graded in every training case.** A search that is too broad also
  fails: records, outside facts, and unrelated facts that share the number are graded
  in each training case. The iteration-5 reminder arm deleted a true quota in 3 of 5
  runs. The reminder here names records and outside facts explicitly, so it is a strong
  competitor.
- **Expected near ceiling for bare arms:** the restraint check of
  `pre-existing-drift-reported`, and the rename itself in `flag-rename-records-stay`.

## Checking the cases

```sh
python incubator/harness.py self-test change-drift-sweep   # references pass, inputs fail
python -B -m unittest discover -s incubator/change-drift-sweep/eval -p "test_*.py"
```

- **Fixture tests:** each fixture's own tests pass on `files/` and on the reference
  (`python -B -m unittest discover -s tests -t .` inside each folder).
- **Hidden tests:** they fail on every `files/` and pass on every reference.
- **Graded variants:** `test_grade.py` holds 107 variants, 34 of them good results worded
  another way, and checks that each fails exactly the checks it should. They cover:
  - search-and-replace into a CHANGELOG, ADR, report or incident;
  - headline-only fixes, and wrong new figures in digits, words and hyphenated adjectives;
  - history narration;
  - a new release heading, or a changelog line above `[Unreleased]`;
  - deleted accurate lines;
  - a silent fix of the pre-existing mismatch, and a reply that hits every keyword
    without reporting it;
  - wordings that must pass: "half an hour", `PAGE_SIZE rows`, a wrapped usage example,
    a doc corrected toward the code and reported.

## Changes after the 2026-11-11 review

Before any run, a review graded 72 hand-built results and found 10 false negatives and 4
false positives or double counts. Every fix is pinned by a variant in `test_grade.py`:
- **New-figure checks** (above) in three cases, and history narration in
  `derived-backoff-total`. Before, a wrong conversion in a living docstring passed every
  check.
- **`derived-backoff-total` check 03** reads every number word up to 999 and hyphenated
  adjectives. "twenty seconds", "a 63-second run" and "twelve attempts" passed before.
- **CHANGELOG check:** new lines only under `[Unreleased]`, and no new release heading,
  as statement 04 of `flag-rename-records-stay` already said.
- **`flag-rename-records-stay`:**
  - a new check, 06, for every other accurate line, including the ADR policy line;
  - check 03 joins a usage example wrapped with backslashes;
  - the prompt now gives a neutral reason and says the behaviour stays. The old reason
    (people asked whether "since" includes the day) invited a change of meaning that had
    nothing to do with drift.
- **`pre-existing-drift-reported`:**
  - check 03 also accepts the flush sentence corrected toward the code. ADR 0001 ("The
    code is the source of truth") and the shipped skill both support that choice, so the
    old leave-only rule tilted the comparison with the shipped-skill arm;
  - check 05 now needs its cues in one paragraph, with a contrast.
- **Held out:** one held-out case was replaced and the other's checks were changed.
  HELD-OUT.md says how and why.

## Changes after the 2026-11-11 derivability gate

The gate ran every case without any skill: Haiku twice, Sonnet once. Six of the seven
cases passed every core check in all three runs, so they could not show a gain, and one
check misgraded a good run. The two held-out cases are among the six; HELD-OUT.md says
what was done with them. [GATE.md](GATE.md) records the results, the grader fix and
what changed in each case. In short:
- `default-value-drift` check 02 no longer reads the ledger's 500-row limit as a page size.
- `unit-spelled-ttl`, `derived-backoff-total`, `flag-rename-records-stay` and
  `pre-existing-drift-reported` each gained statements that a search for the old literal
  does not find, mostly in files that never name the changed setting. Each is pinned by a
  variant in `test_grade.py`.
- Gate runs are for case selection only. No skill edit was decided from them.

## Reserve cases (not built)

- `upload-limit-ts`: the same value drift in TypeScript JSDoc and a README (10 MB written
  as 10485760 bytes). It needs a Node test runner, or Python hidden tests that read the
  TS constant.
- `moved-module-links`: Markdown link targets after a file move. The shipped
  `stale-refs` already catches the code-comment path, so only the link would
  discriminate.
- `default-arg-shared-number`: a docstring in another module says "5-second" without
  naming the parameter, beside an unrelated `POOL_SPARE = 5`.
- `living-page-in-dated-folder`: a page that says how the code works now, filed under a
  dated folder (`docs/2026-q3/`), so the script marks it `record?` and it must still be
  corrected. It tests the path-hint limit from the side of a false `record?` hint.
- `help-text-drift`: an argparse `help=` string that states the old default, which only
  `--strings` or a grep finds.
