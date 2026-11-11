# Fate list for docs/digests.md

Page status: kept, not deleted. Two kept claims remain (the cleanup-ordering sentence and the mail-provider incident bullet), so the page holds only those. The page was not deleted because kept claims remain.

| # | Claim (page order) | Fate | Evidence / destination |
|---|---|---|---|
| 1 | "The digest job runs after the nightly notification cleanup, so a digest never includes notifications that the cleanup removed." | Kept | Scheduler and cleanup are not in this repo. `build_digest` only filters on `read`, so no code here relies on the order. Gap: job schedule and cleanup live elsewhere. |
| 2 | "`build_digest()` groups a user's unread notifications by project." | Dropped | `notify/digest.py` lines 14-19 state it. |
| 3 | "`due()` holds back a user's next digest until 24 hours after the last one" | Not migrated | `notify/settings.py` line 4: `MIN_HOURS_BETWEEN_DIGESTS = 6`, used by `notify/digest.py` line 11. Code says 6 hours, page says 24. Which side is right? |
| 4 | "because users on busy projects complained about digest floods in the 2025 survey (NOTIF-9)" | Moved | `notify/settings.py`, comment above `MIN_HOURS_BETWEEN_DIGESTS`. The reason is kept; the value is not repeated. |
| 5 | "Subjects are cut to `SUBJECT_LIMIT` (78) characters" | Dropped | `notify/mail.py` line 3 (`SUBJECT_LIMIT = 78`) and line 8 (truncation). |
| 6 | "because the company mail relay folds longer subject headers, and some mail clients then show the subject garbled (MAIL-71)" | Moved | `notify/mail.py`, comment above `SUBJECT_LIMIT`. Ticket id kept. |
| 7 | "During a mail-provider incident, support pauses all sending from the provider's dashboard. Ask in #mail-ops before pausing." | Kept | Operational steps. Left as written on the page. |

Heading "# Notification digests" is not a claim; it stays because kept text remains under it.

Edits made:
- `notify/settings.py`: two comment lines added above `MIN_HOURS_BETWEEN_DIGESTS`.
- `notify/mail.py`: two comment lines added above `SUBJECT_LIMIT`.
- `docs/digests.md`: removed claims 2, 3, 4, 5 and 6. Claims 1 and 7 kept as written.
- No code, tests, README, AGENTS.md or oncall.md changed. Unit tests pass (`python -m unittest discover -s tests -t .`, 3 tests OK).

Other files:
- No other input file states a moved fact. `AGENTS.md` mentions settings living in `notify/settings.py` but not the values.
- Nothing links to `docs/digests.md` or its sections.
- `tests/test_digest.py` reads the constants and does not pin 24 or 6.

Gaps for the user:
- Decide 24 hours (page) versus 6 hours (code). If 24 is right, `MIN_HOURS_BETWEEN_DIGESTS` must change; that is a code change this exercise did not make. Claim 3 then stays not migrated until resolved.
- Facts about the mail relay (MAIL-71) and the 2025 survey (NOTIF-9) come from outside this repo; they are moved as written and cannot be checked here.
- The cleanup ordering (claim 1) depends on another system; it stays on the page.
- Claim 7 stays on the page; #mail-ops is an outside channel.
- `RESPONSE.md` was added at the task's request, even though the skill says to add no file.
