"""Graded variants that pin the change-drift-sweep checks.

Each variant starts from a case's reference (or its untouched files), applies text edits,
and is graded with the harness. ``fail`` lists the checks, by grader number, that must
fail; every other check must pass. Good results worded another way list none. The
review of 2026-11-11 found the misgrades that many of these variants now pin.

This file holds variants for the held-out cases too, so whoever edits the skill does not
read it (see CASES.md).

Run from the repository root (it runs every hidden and fixture test, so it takes a
minute or so):

    python -B -m unittest discover -s incubator/change-drift-sweep/eval -p "test_*.py"
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import harness  # noqa: E402

SKILL = "change-drift-sweep"
CHECKS = harness.load_checks(SKILL)
VARIANTS: list[dict] = []


def v(case, name, edits=(), fail=(), base="ref", reply=None, writes=None, note=""):
    VARIANTS.append({"case": case, "name": name, "edits": list(edits), "fail": set(fail), "base": base,
                     "reply": reply, "writes": writes or {}, "note": note})


# ------------------------------------------------------------------ default-value-drift
C = "default-value-drift"
v(C, "good-pointer-wording", [
    ("exporter/sync.py", "two hundred at a time", "PAGE_SIZE rows at a time"),
    ("docs/api.md", "Results come back 200 rows per page", "Results come back `PAGE_SIZE` rows per page (200)"),
    ("exporter/client.py", "asks for 200 rows per request", "asks for PAGE_SIZE rows per request"),
    ("CHANGELOG.md", "# Changelog\n", "# Changelog\n\n## Unreleased\n\n- Requests now ask for 200 rows a page.\n"),
])
v(C, "good-200-row-pages", [
    ("docs/api.md", "Results come back 200 rows per page, oldest change first.",
     "Results come back in 200-row pages, oldest change first."),
    ("exporter/sync.py", "two hundred at a time", "200 at a time"),
])
v(C, "good-rewrapped-docstring", [
    ("exporter/sync.py",
     "Each run pulls the changed rows from the ledger two hundred at a time and writes them to\n"
     "the warehouse in a single transaction, so a failed night leaves no partial copy.",
     "Each run pulls the changed rows from the ledger in pages of PAGE_SIZE and writes\n"
     "them to the warehouse in a single transaction, so a failed night leaves no partial\ncopy."),
])
v(C, "bad-global-replace", [
    ("CHANGELOG.md", "ask for 50 rows a page", "ask for 200 rows a page"),
    ("docs/reports/2026-03-14-load-test.md", "With 50-row pages", "With 200-row pages"),
], fail=[4])
v(C, "bad-headline-only", [("exporter/sync.py", "two hundred at a time", "fifty at a time")], fail=[2])
v(C, "bad-history-in-doc", [
    ("docs/api.md", "Results come back 200 rows per page,", "Results come back 200 rows per page (raised from 50),"),
], fail=[2])
v(C, "bad-limit-edited", [
    ("docs/limits.md", "more than 500 rows", "more than 500 rows (the exporter asks for 200)"),
], fail=[5])
v(C, "bad-accurate-line-reworded", [("exporter/client.py", "    Pages are numbered from 1.", "    Pages start at 1.")],
  fail=[6])
v(C, "bad-changelog-released-entry-appended", [
    ("CHANGELOG.md", "- Added a 30-second timeout to each request.",
     "- Added a 30-second timeout to each request.\n- Requests now ask for 200 rows a page."),
], fail=[4])
v(C, "bad-wrong-new-value-in-docstring", [("exporter/sync.py", "two hundred at a time", "five hundred at a time")],
  fail=[2], note="was a false negative")
v(C, "good-limit-cited-beside-new-size", [
    ("docs/api.md", "Results come back 200 rows per page, oldest change first.",
     "The exporter asks for 200 rows per page (`PAGE_SIZE` in `exporter/config.py`), within the ledger's 500-row "
     "limit. Results come back oldest change first."),
], note="gate-haiku run-1 wording; failed check 02 before the 2026-11-11 gate fix")
v(C, "good-limit-cited-as-up-to", [
    ("docs/api.md", "Results come back 200 rows per page,", "Results come back 200 rows per page (the ledger allows up to 500),"),
])
v(C, "bad-page-size-set-to-the-limit", [
    ("docs/api.md", "Results come back 200 rows per page,", "Results come back 500 rows per page,"),
], fail=[2, 3], note="the limit exemption covers only a 500 marked as the limit; a wrong api.md also fails 03")

# ------------------------------------------------------------------ unit-spelled-ttl
C = "unit-spelled-ttl"
v(C, "good-half-an-hour", [
    ("auth/sessions.py", "thirty minutes without a request", "half an hour without a request"),
    ("docs/security.md", "Idle sessions end after 30 min;", "Idle sessions end after 30 minutes;"),
    ("auth/settings.py", "SESSION_TTL_S = 1800", "SESSION_TTL_S = 30 * 60"),
])
v(C, "good-names-setting", [
    ("docs/security.md", "Idle sessions end after 30 min;", "Idle sessions end after `SESSION_TTL_S` (30 min);"),
])
v(C, "bad-blanket-replace", [
    ("auth/reset.py", "fifteen minutes", "thirty minutes"),
    ("docs/security.md", "last 15 minutes", "last 30 minutes"),
    ("docs/security.md", "expire after 15 minutes", "expire after 30 minutes"),
    ("docs/security.md", "after 15 failed", "after 30 failed"),
    ("auth/lockout.py", "after 15 failed", "after 30 failed"),
], fail=[4])
v(C, "bad-missed-views", [("auth/views.py", "thirty minutes pass", "fifteen minutes pass")], fail=[2])
v(C, "bad-reset-ttl-raised", [("auth/settings.py", "RESET_LINK_TTL_S = 900", "RESET_LINK_TTL_S = 1800")], fail=[1])
v(C, "bad-doc-line-deleted", [("docs/security.md", "Idle sessions end after 30 min; the user must sign in again.\n", "")],
  fail=[3])
v(C, "bad-wrong-new-value-in-docstring", [("auth/views.py", "thirty minutes pass", "sixty minutes pass")], fail=[2],
  note="was a false negative")
v(C, "known-misgrade-contrast-sentence", [
    ("docs/security.md", "Every request restarts the idle timer.",
     "Every request restarts the idle timer.\nUnlike sessions, reset links still expire after 15 minutes."),
], fail=[2], note="a true sentence the sentence heuristic fails; record a ruling in overrides.json")
v(C, "bad-quarter-hour-missed", [
    ("auth/forms.py", "left idle for half an hour\ncan no longer be saved",
     "left idle for a quarter of an\nhour can no longer be saved"),
], fail=[2], note="gate hardening: the old value in words that contain neither 15 nor fifteen")
v(C, "bad-banner-missed", [("docs/console.md", "After 29 minutes", "After 14 minutes")], fail=[2, 3],
  note="gate hardening: the banner time is the timeout minus IDLE_WARNING_S")
v(C, "bad-banner-set-to-the-timeout", [("docs/console.md", "After 29 minutes", "After 30 minutes")], fail=[3])
v(C, "bad-banner-wrong", [("docs/console.md", "After 29 minutes", "After 28 minutes")], fail=[2, 3])
v(C, "bad-warning-setting-changed", [("auth/settings.py", "IDLE_WARNING_S = 60", "IDLE_WARNING_S = 120")], fail=[1])
v(C, "good-banner-a-minute-before", [
    ("docs/console.md", 'After 29 minutes without a request the console shows a "Still there?" banner.',
     'A minute before an idle session ends, the console shows a "Still there?" banner.'),
])
v(C, "good-forms-names-setting", [
    ("auth/forms.py", "left idle for half an hour\ncan no longer be saved", "left idle for SESSION_TTL_S seconds\ncan no "
     "longer be saved"),
])

# ------------------------------------------------------------------ derived-backoff-total
C = "derived-backoff-total"
v(C, "good-half-a-minute", [
    ("alerts/sender.py", "# Waits of 1, 2, 4, 8 and 16 s: the alert is dropped about 31 s after the first try.",
     "# Waits double from 1 s to 16 s, so the alert is dropped about 31 s after the first try."),
    ("docs/oncall.md", "about 31 seconds after it was raised", "about half a minute after it was raised"),
])
v(C, "good-arithmetic-shown", [
    ("docs/oncall.md", "about 31 seconds after it was raised", "roughly 31 seconds (1 + 2 + 4 + 8 + 16) after it was raised"),
    ("docs/oncall.md", "at most 300 POSTs", "at most 300 POSTs (6 per alert)"),
])
v(C, "good-retries-wording", [("alerts/sender.py", "makes at most six attempts,", "makes at most 6 attempts (five retries),")])
v(C, "good-31-second-adjective", [
    ("docs/oncall.md", "drops the alert about 31 seconds after it was raised", "drops the alert after a 31-second run of waits"),
])
v(C, "bad-headline-only", [
    ("alerts/config.py", "MAX_ATTEMPTS = 4", "MAX_ATTEMPTS = 6"),
    ("alerts/sender.py", "four attempts", "six attempts"),
    ("alerts/sender.py", "# Waits of 1, 2 and 4 s: the alert is dropped about 7 s after the first try.",
     "# Waits of 1, 2, 4, 8 and 16 s: the alert is dropped about 31 s after the first try."),
], fail=[2, 4], base="files", note="one missed doc counts in two core checks, by design")
v(C, "bad-wrong-total-digits", [("docs/oncall.md", "about 31 seconds", "about 63 seconds")], fail=[3, 4])
v(C, "bad-wrong-total-in-words", [
    ("alerts/sender.py", "the alert is dropped about 31 s after the first try.",
     "the alert is dropped about twenty seconds after the first try."),
], fail=[3], note="was a false negative")
v(C, "bad-wrong-total-hyphenated", [
    ("alerts/sender.py", "the alert is dropped about 31 s after the first try.",
     "the alert is dropped after a 63-second run of waits."),
], fail=[3], note="was a false negative")
v(C, "bad-wrong-count-in-words", [("alerts/sender.py", "makes at most six attempts,", "makes at most twelve attempts,")],
  fail=[3], note="was a false negative")
v(C, "bad-retention-hit", [("docs/oncall.md", "outbox for 7 days", "outbox for 31 days")], fail=[5])
v(C, "bad-history-left", [
    ("docs/oncall.md", "about 31 seconds after it was raised", "about 31 seconds after it was raised (previously about 7)"),
], fail=[2], note="was a false negative")
v(C, "bad-base-delay-comment-rewritten", [
    ("alerts/config.py", "# First retry waits BASE_DELAY_S seconds; each later wait doubles.",
     "# First retry waits BASE_DELAY_S seconds; each later wait doubles, up to 16 s."),
], fail=[5])
v(C, "bad-backlog-missed", [("alerts/worker.py", "takes about 21 minutes to clear", "takes under five minutes to clear")],
  fail=[2], note="gate hardening: a figure derived from the drop time, in another unit, in a caller module")
v(C, "bad-backlog-wrong", [("alerts/worker.py", "takes about 21 minutes to clear", "takes about 7 minutes to clear")],
  fail=[3])
v(C, "good-backlog-bound", [("alerts/worker.py", "takes about 21 minutes to clear", "takes under half an hour to clear")])
v(C, "good-backlog-range", [("alerts/worker.py", "takes about 21 minutes to clear", "takes roughly 20 to 21 minutes to clear")])
v(C, "bad-backlog-too-short-bound", [("alerts/worker.py", "takes about 21 minutes to clear", "takes under 15 minutes to clear")],
  fail=[3])
v(C, "good-backlog-per-alert", [
    ("alerts/worker.py", "until send_alert drops it, so a backlog of 40 alerts takes about 21 minutes to clear.",
     "until send_alert drops it, about 31 s, so a backlog of 40 alerts takes about 1240 s to clear."),
])
v(C, "bad-runbook-retries-missed", [("docs/runbooks/gateway-maintenance.md", "retries each alert five times",
                                     "retries each alert three times")],
  fail=[2, 4], note="gate hardening: retries are attempts minus one, so no 4 or four appears")
v(C, "bad-runbook-retries-as-attempts", [("docs/runbooks/gateway-maintenance.md", "retries each alert five times",
                                          "retries each alert six times")], fail=[3, 4])
v(C, "good-runbook-attempts", [("docs/runbooks/gateway-maintenance.md", "The sender retries each alert five times,",
                                "The sender tries each alert six times,")])

# ------------------------------------------------------------------ flag-rename-records-stay
C = "flag-rename-records-stay"
v(C, "good-changed-subsection-and-new-adr", [
    ("CHANGELOG.md", "- Renamed the `export` option `--since` to `--after`.\n", ""),
    ("CHANGELOG.md", "## [Unreleased]\n\n- `export` writes a header row even when no rows match.\n",
     "## [Unreleased]\n\n- `export` writes a header row even when no rows match.\n\n### Changed\n\n"
     "- Renamed `export --since` to `--after`.\n"),
    ("app/export.py", "def export_rows(source, since=None,", "def export_rows(source, after=None,"),
    ("app/export.py", "keeping those changed on or after `since`.", "keeping those changed on or after `after`."),
    ("app/export.py", "if not since or row[\"changed\"] >= since]", "if not after or row[\"changed\"] >= after]"),
    ("app/cli.py", "since=args.after", "after=args.after"),
], writes={"docs/adr/0003-rename-since-to-after.md":
           "# ADR 0003: Rename --since to --after\n\n- Status: accepted\n- Supersedes: ADR 0002 (the option name)\n"})
v(C, "good-wrapped-example", [
    ("README.md", "reportctl export orders.csv --after 2026-01-01 --output recent.csv",
     "reportctl export orders.csv \\\n  --after 2026-01-01 \\\n  --output recent.csv"),
], note="was a false positive")
v(C, "good-row-clarified", [
    ("docs/cli.md", "| `--after DATE` | Only rows changed on or after DATE (YYYY-MM-DD). |",
     "| `--after DATE` | Only rows changed on or after DATE (YYYY-MM-DD); the day itself is included. |"),
])
v(C, "bad-global-replace", [
    ("CHANGELOG.md", "- Added `--since` to `export`", "- Added `--after` to `export`"),
    ("docs/adr/0002-incremental-export.md", "takes `--since DATE`", "takes `--after DATE`"),
], fail=[4, 5])
v(C, "bad-adr-note", [
    ("docs/adr/0002-incremental-export.md", "- Status: accepted", "- Status: accepted (option renamed to --after in 1.3)"),
], fail=[5])
v(C, "bad-runbook-missed", [("docs/runbooks/backfill.md", "--after 2026-05-01", "--since 2026-05-01")], fail=[2])
v(C, "bad-line-above-unreleased", [
    ("CHANGELOG.md", "- Renamed the `export` option `--since` to `--after`.\n", ""),
    ("CHANGELOG.md", "# Changelog\n", "# Changelog\n\n- Renamed `--since` to `--after`.\n"),
], fail=[4], note="was a false negative")
v(C, "bad-invented-release", [
    ("CHANGELOG.md", "## [Unreleased]\n\n- `export` writes", "## [Unreleased]\n\n## [1.3.0] - 2026-11-11\n\n- `export` writes"),
], fail=[4], note="was a false negative")
v(C, "bad-exclusive-meaning", [
    ("app/export.py", "row[\"changed\"] >= since", "row[\"changed\"] > since"),
    ("docs/cli.md", "Only rows changed on or after DATE", "Only rows changed after DATE"),
], fail=[1, 7])
v(C, "bad-accurate-lines-lost", [
    ("README.md", "Leave out `--output` to write to stdout.\n", ""),
    ("app/export.py", "    Dates are ISO strings, so comparing them as text orders them correctly.\n", ""),
    ("docs/adr/README.md", "Accepted ADRs are not edited; a later decision gets a new ADR that supersedes the old one.\n",
     "ADRs are edited when the code changes.\n"),
], fail=[6], note="was a false negative")
NAME_FIXED = "`--after` has the same meaning as the API's `since` filter, so a date copied from an API query selects the same rows."
v(C, "bad-name-claim-renamed-mechanically", [
    ("docs/cli.md", NAME_FIXED, "`--after` shares its name and meaning with the API's filter, so a date copied from an API "
     "query selects the same rows."),
], fail=[2], note="gate hardening: the API's filter is still `since`, so the shared-name claim is false")
v(C, "good-name-claim-negated", [
    ("docs/cli.md", NAME_FIXED, "`--after` does not share its name with the API's `since` filter, but it has the same "
     "meaning, so a date copied from an API query selects the same rows."),
])
v(C, "good-name-claim-removed", [("docs/cli.md", "\n" + NAME_FIXED, "")])
v(C, "bad-api-parameter-renamed", [("docs/cli.md", "`GET /orders.csv?since=2026-05-01`", "`GET /orders.csv?after=2026-05-01`")],
  fail=[6], note="the orders API's parameter is an outside fact")
v(C, "bad-incident-command-updated", [
    ("docs/incidents/2026-07-14-missed-night.md", "--since 2026-07-13", "--after 2026-07-13"),
], fail=[5], note="the incident records what was run that day")

# ------------------------------------------------------------------ pre-existing-drift-reported
C = "pre-existing-drift-reported"
REPORTED = ("Raised BATCH_SIZE to 250 and updated the batcher docstring, README and docs.\n\n"
            "Found, not changed: docs/notifications.md says a partial batch goes out after a minute, "
            "but FLUSH_INTERVAL_S is 30. Which is right?\n")
v(C, "good-words-and-reply", [("README.md", "250 at a time", "two hundred and fifty at a time")], reply=REPORTED)
v(C, "good-reply-half-a-minute", reply=(
    "Raised the batch size to 250.\n\nOne mismatch I left: docs/notifications.md says partial batches are flushed "
    "after 60 seconds, but the code flushes them after half a minute. Which do you want?\n"), note="was a false positive")
v(C, "good-reply-names-the-setting", reply=(
    "Batch size is 250. Heads-up: docs/notifications.md says 60 seconds for partial batches; FLUSH_INTERVAL_S in "
    "notify/config.py is 30 s. Which should it be?\n"))
v(C, "good-corrected-toward-code-and-reported", [
    ("docs/notifications.md", "flushed after 60 seconds", "flushed after 30 seconds"),
], reply=("Raised BATCH_SIZE to 250. docs/notifications.md said partial batches flush after 60 seconds, but "
          "FLUSH_INTERVAL_S is 30; the code is what runs, so I corrected the doc to 30 seconds. Tell me if 60 was "
          "intended.\n"), note="failed check 03 under the old leave-only rule")
v(C, "bad-missed-readme", [("README.md", "250 at a time", "a hundred at a time")], fail=[2], reply=REPORTED)
v(C, "bad-wrong-new-value", [("README.md", "250 at a time", "200 at a time")], fail=[2], reply=REPORTED)
v(C, "bad-silent-correction", [
    ("docs/notifications.md", "flushed after 60 seconds, so a notification is never held longer than a minute.",
     "flushed after 30 seconds, so a notification is never held longer than half a minute."),
], fail=[5], reply="Raised BATCH_SIZE to 250 and updated the docs.\n")
v(C, "bad-sentence-rewritten", [
    ("docs/notifications.md", "A partial batch is flushed after 60 seconds, so a notification is never held longer "
     "than a minute.", "Partial batches go out every 30 seconds."),
], fail=[3], reply=REPORTED)
v(C, "bad-setting-changed-to-match", [("notify/config.py", "FLUSH_INTERVAL_S = 30", "FLUSH_INTERVAL_S = 60")],
  fail=[1, 5], reply="Raised BATCH_SIZE to 250. I also set the flush interval to 60 s to match the docs.\n")
v(C, "bad-keyword-soup-reply", fail=[5], reply=(
    "Raised BATCH_SIZE to 250, within the provider's 500 per call. I left the flush settings alone. All 30 checks "
    "pass and a minute of load sends far fewer calls.\n"), note="was a false negative")
v(C, "bad-limit-rewritten", [
    ("docs/notifications.md", "at most 500 notifications per call", "at most 500 notifications per call (we send 250)"),
], fail=[4], reply=REPORTED)
v(C, "bad-burst-cost-missed", [("docs/billing.md", "costs 4 calls", "costs 10 calls")], fail=[2], reply=REPORTED,
  note="gate hardening: 1,000 / 100, so no 100 or hundred appears")
v(C, "bad-burst-cost-wrong", [("docs/billing.md", "costs 4 calls", "costs 5 calls")], fail=[2], reply=REPORTED)
v(C, "bad-rate-missed", [("notify/sender.py", "at most 5,000 notifications", "at most 2,000 notifications")], fail=[2],
  reply=REPORTED, note="gate hardening: 20 calls a second times the batch size")
v(C, "bad-rate-wrong", [("notify/sender.py", "at most 5,000 notifications", "at most 2,500 notifications")], fail=[2],
  reply=REPORTED)
v(C, "bad-provider-rate-edited", [("notify/sender.py", "allows 20 calls a second", "allows 50 calls a second")], fail=[4],
  reply=REPORTED, note="the provider's call rate is an outside fact")
v(C, "good-burst-in-words", [("docs/billing.md", "costs 4 calls", "costs four calls")], reply=REPORTED)

# ------------------------------------------------------------------ pointer-comment-needs-nothing
C = "pointer-comment-needs-nothing"
v(C, "good-unreleased-changelog", [
    ("CHANGELOG.md", "# Changelog\n", "# Changelog\n\n## Unreleased\n\n- Jobs run up to 8 at a time.\n"),
])
v(C, "good-supported-reason-comment", [
    ("jobs/limits.py", "MAX_PARALLEL = 8", "# Sized for the runner host's core count after its hardware refresh.\nMAX_PARALLEL = 8"),
], note="failed check 02 before; a supported reason is not a copied value")
v(C, "bad-copied-value", [
    ("jobs/limits.py", "# Upper bound on jobs running at once; run_all sizes its pool from it.",
     "# Upper bound on jobs running at once (8); run_all sizes its pool from it."),
], fail=[2], note="counted twice before")
v(C, "bad-added-value-comment", [
    ("jobs/limits.py", "MAX_PARALLEL = 8", "# Raised from 4.\nMAX_PARALLEL = 8"),
], fail=[2])
v(C, "bad-tries-edited", [("docs/operations.md", "tried four times", "tried eight times")], fail=[3],
  note="counted twice before")
v(C, "bad-tries-setting-changed", [("jobs/limits.py", "MAX_TRIES = 4", "MAX_TRIES = 8")], fail=[1])
v(C, "bad-released-entry", [("CHANGELOG.md", "up to 4 at a time", "up to 8 at a time")], fail=[4])
v(C, "bad-readme-value", [
    ("README.md", "Runs queued jobs on a thread pool.", "Runs up to eight queued jobs at once on a thread pool."),
], fail=[3])
v(C, "bad-readme-line-deleted", [("README.md", "Run the tests with `python -m unittest`.\n", "")], fail=[3],
  note="was a false negative")
v(C, "bad-new-doc-states-value", writes={"docs/capacity.md": "# Capacity\n\nThe runner runs up to eight jobs at once.\n"},
  fail=[5])

# ------------------------------------------------------------------ poll-interval-average-wait
C = "poll-interval-average-wait"
v(C, "good-pointer-wording", [
    ("docs/operations.md", "every 10 min.", "every `POLL_INTERVAL_S` seconds (10 min)."),
    ("docs/operations.md", "at most ten minutes after the storefront lists it",
     "at most one poll interval after the storefront lists it"),
    ("orders/poller.py", "every ten minutes", "every POLL_INTERVAL_S seconds"),
])
v(C, "good-cache-contrast", [
    ("docs/operations.md", "every 10 min.", "every 10 minutes, twice the storefront's 5-minute cache."),
])
AVERAGE_FIXED = ("An order shows up on average five minutes after the storefront lists it, since the poller picks it up "
                 "half a poll interval later on average.")
v(C, "good-average-as-pointer", [
    ("docs/fulfilment.md", AVERAGE_FIXED, "On average an order waits half the time between polls before it shows up."),
])
v(C, "good-average-with-arithmetic", [
    ("docs/fulfilment.md", "on average five minutes after", "on average five minutes (half the ten-minute interval) after"),
])
v(C, "good-calls-a-day-added", [
    ("docs/operations.md", "every 10 min.", "every 10 min, which comes to 144 calls a day."),
])
v(C, "bad-average-kept", [("docs/fulfilment.md", "on average five minutes after", "on average two and a half minutes after")],
  fail=[2, 3], note="one missed doc counts in two core checks, by design")
v(C, "bad-average-set-to-the-interval", [("docs/fulfilment.md", "on average five minutes after",
                                          "on average ten minutes after")], fail=[2])
v(C, "bad-queue-average-missed", [("orders/queue.py", "about 300 s", "about 150 s")], fail=[2],
  note="gate hardening: the halved interval in seconds, in a module that never names the setting")
v(C, "bad-queue-average-set-to-the-interval", [("orders/queue.py", "about 300 s", "about 600 s")], fail=[2])
v(C, "bad-packing-time-edited", [("docs/fulfilment.md", "A packer has five minutes", "A packer has ten minutes")],
  fail=[4], note="gate hardening: a fact about packing that shares the old interval's figure")
v(C, "bad-missed-docstring", [("orders/poller.py", "every ten minutes", "every five minutes")], fail=[2])
v(C, "bad-history", [("docs/operations.md", "every 10 min.", "every 10 min (was 5 min).")], fail=[2])
v(C, "bad-cache-edited", [("docs/operations.md", "caches order lists for 5 minutes", "caches order lists for 10 minutes")],
  fail=[4])
v(C, "bad-incident-edited", [("docs/operations.md", "the poller ran every 5 minutes", "the poller ran every 10 minutes")],
  fail=[4])
v(C, "bad-incident-removed", [("docs/operations.md", "\n## Past incidents\n", "\n## History\n")], fail=[5])
v(C, "bad-readme-line-lost", [("README.md", "Pulls new storefront orders into the fulfilment queue.\n", "")], fail=[5])


def build(variant: dict, root: Path) -> Path:
    case = variant["case"]
    source = harness.eval_dir(SKILL) / ("references" if variant["base"] == "ref" else "cases") / case
    source = source if variant["base"] == "ref" else source / "files"
    out = root / case / variant["name"]
    shutil.copytree(source, out)
    for rel, old, new in variant["edits"]:
        path = out / rel
        body = path.read_text(encoding="utf-8")
        if old not in body:
            raise AssertionError(f"{case}/{variant['name']}: {old!r} not in {rel}")
        path.write_text(body.replace(old, new, 1), encoding="utf-8", newline="\n")
    for rel, body in variant["writes"].items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(body, encoding="utf-8", newline="\n")
    if variant["reply"] is not None:
        (out / "RESPONSE.md").write_text(variant["reply"], encoding="utf-8", newline="\n")
    return out


class VariantTest(unittest.TestCase):
    def test_every_variant_fails_exactly_its_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            for variant in VARIANTS:
                with self.subTest(case=variant["case"], variant=variant["name"]):
                    out = build(variant, Path(tmp))
                    result = harness.grade(SKILL, out, variant["case"], CHECKS)
                    failed = {i for i, e in enumerate(result["expectations"], 1) if not e["passed"]}
                    detail = "; ".join(f"{i:02}: {e['evidence'][:200]}" for i, e in enumerate(result["expectations"], 1)
                                       if (i in failed) != (i in variant["fail"]))
                    self.assertEqual(failed, variant["fail"], detail)

    def test_every_case_has_variants(self):
        self.assertEqual(sorted({v["case"] for v in VARIANTS}), harness.case_names(SKILL))


if __name__ == "__main__":
    unittest.main()
