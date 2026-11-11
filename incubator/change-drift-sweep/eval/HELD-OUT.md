# change-drift-sweep held-out cases

**Do not read this file before writing or editing the skill.** It describes the two
held-out cases. They are run once, at the end, as a check on overfitting, and are never
used to decide a skill edit. [CASES.md](CASES.md) describes the five training cases and
how every case is graded.

| Case | Behaviour | Trap | Where the needed evidence lives | Heuristic checks |
| --- | --- | --- | --- | --- |
| `pointer-comment-needs-nothing` | Restraint: comments that name the constant, not its value, need no edit. | `MAX_PARALLEL` 4 to 8. Every mention is a pointer (`MAX_PARALLEL`). A sweep for 4 or four finds only other facts and records: `MAX_TRIES` is also 4 ("tried four times"), the dashboard refreshes every four seconds, and there is a 0.4.0 CHANGELOG entry and a dated capacity report. Copying "8" into a comment, adding "raised from 4", or editing any of those fails. A new comment that gives the user's stated reason (the hardware refresh), with no value and no history, passes. This is a guard against a skill that makes agents over-edit, and bare arms are expected near ceiling. | `jobs/limits.py`, `jobs/runner.py`, `docs/operations.md`, `README.md`, `CHANGELOG.md`, `docs/reports/2026-09-02-nightly-capacity.md` | 02 and 05 (keyword regex on added lines) |
| `poll-interval-average-wait` | Generalisation: a figure derived from the old value by a form SKILL.md does not list (halving it for an average wait), and a dated record that sits inside a living page, where no path hint marks it. | `POLL_INTERVAL_S` 300 to 600. Prose says "every five minutes", "every 5 min" and "at most five minutes after", never 300. `docs/fulfilment.md`, the packing team's page, says an order shows up "on average two and a half minutes after the storefront lists it", half a poll interval, which must become five minutes. The `orders/queue.py` docstring, in a module that never names the setting, says an order "has already waited about 150 s on average" when it is queued, which must become about 300 s. Neither figure contains the old value, and a search for 5, five or 300 misses both. The storefront's 5-minute cache and its 10,000-a-day quota are outside facts, and the packers' "five minutes to confirm a picked order" is about something else. The "Past incidents" section of `docs/operations.md` dates its entry (2 October 2026) and says the poller ran every 5 minutes "at the time". It is a record inside a living page, and the script gives it no `record?` hint. | `orders/settings.py`, `orders/poller.py`, `orders/queue.py`, `docs/fulfilment.md`, `docs/operations.md` ("Storefront limits" and "Past incidents" sections) | 02 (sentence regex and new-figure check), 03 (sentence regex) |

## How the held-out cases are graded

`pointer-comment-needs-nothing`. Each check owns its own files, so no mistake counts twice:
- 02: `jobs/`. Every existing comment and docstring is kept word for word, and no line added
  there states 8, eight, "was 4", "from 4" or a word such as raised or previously.
- 03: `docs/operations.md` and `README.md`, byte for byte.
- 04: the dated report, and the released CHANGELOG sections.
- 05: every other file, for added lines that state the value or its history. A new
  CHANGELOG line is not checked; history belongs there.

`poll-interval-average-wait`:
- **Check 02:**
  - no sentence about polling states the old interval or the old longest delay;
  - no sentence states the old average (two and a half minutes, 2.5 min, 150 s), in
    `docs/fulfilment.md`, `orders/queue.py` or anywhere else;
  - every changed or added sentence gives figures that fit ten-minute polls: 600 s for the
    interval and the longest delay, and 300 s in a sentence about the average wait. "half
    the ten-minute interval" reads as 300 s. A sentence about the cache may give either.
- **Check 03:** `docs/fulfilment.md` still gives the average wait, as five minutes or as
  half the time between polls, and `docs/operations.md` gives the new interval.
- **Check 04:** the cache and quota sentences, the packers' five minutes, and every line
  of the incident entry are kept word for word.

## Why `poll-interval-per-day` was replaced

The review of 2026-11-11 found that both held-out cases tested rules SKILL.md states
outright, so neither could show whether the skill generalises beyond its own list:
- `poll-interval-per-day` graded a per-day count found by division (86,400 / 300 = 288).
  SKILL.md lists "a per-hour or per-day count", and its arithmetic example,
  `86400 // 10800`, is the same calculation. The skill writer had also read CASES.md,
  which then described the held-out cases in detail.
- `pointer-comment-needs-nothing` tests "a comment that names the constant ... leave it
  word for word", which SKILL.md says in so many words. It stays as a restraint guard: it
  can catch a skill that makes agents over-edit, but it is not a generalisation test.

`poll-interval-average-wait` keeps the old case's code, settings, hidden tests and
outside facts. It drops the per-day count and adds two things SKILL.md does not name:
- a figure derived by halving: an average wait;
- a dated record that sits as a section of a living page.

Its design was chosen by reading SKILL.md for what it leaves out, which is the point of
a held-out case. No skill text, script or example was changed because of it. In
particular, `value_drift.py` does not match "two and a half minutes" even when the
derived 150 s is passed, and that was left as it is.

This file was split out of CASES.md at the same time, so that a skill writer who reads
the eval design no longer reads the held-out cases. The pointer case was already
described in CASES.md when the skill was written, so it remains contaminated in that
sense. The new case has never been described anywhere a skill writer reads.

## Changes after the 2026-11-11 derivability gate

The gate ran both held-out cases without any skill (Haiku twice, Sonnet once). Both passed
every check in all three runs. [GATE.md](GATE.md) has the per-case counts; the held-out
details are only here.

- `pointer-comment-needs-nothing` is unchanged. It is a deliberate restraint control:
  the right edit is one constant, and bare arms are meant to be at ceiling. Its value is
  catching a skill that makes agents over-edit, so it cannot and need not show a gain.
- `poll-interval-average-wait` was at ceiling because the average sat in the README,
  the first file every run read. All three runs changed it to five minutes and kept the
  incident entry. The case was hardened for the same two behaviours:
  - the halved figure moved from the README to `docs/fulfilment.md`, a page the README
    does not link;
  - a second halved figure, in seconds ("about 150 s"), was added to a new
    `orders/queue.py` docstring, in a module that never names `POLL_INTERVAL_S`;
  - a distractor that shares the old figure, the packers' five minutes to confirm an
    order, was added beside the average; a blanket replace of "five minutes" breaks it.

  The code, settings, hidden tests, outside facts and the incident entry are unchanged.
  Replaying the three gate runs' exact edits on the hardened fixture fails checks 02 and
  03 in each. That shows only that the old edits are no longer enough; whether a bare
  model now finds the moved figures needs a new gate run.

The hardening was designed from the gate runs and from this file. SKILL.md was not read
for it, and no skill text, script or example was changed because of it.

## Expected outcomes

- `pointer-comment-needs-nothing`: bare arms at ceiling, by design. A drop for
  `with_skill` would mean the skill causes over-editing.
- `poll-interval-average-wait`: the most likely misses are the two halved figures,
  which only reading or a search for "average" or "poll" finds, and an edit to the
  incident entry or the packers' five minutes by a run that treats every "five minutes"
  as the interval. A with-skill run that passes only the listed forms and misses the
  averages would show the skill's list does not generalise.
