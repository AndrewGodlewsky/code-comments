I moved the digest facts that describe code behaviour into comments next to that code. I did not change any code, and the tests still pass (3 of 3).

What moved:
- `notify/digest.py`, `build_digest()`: docstring stating that the digest job runs after the nightly notification cleanup, so removed notifications never reach its input.
- `notify/mail.py`, `SUBJECT_LIMIT`: comment on why subjects are cut at 78 characters (the company mail relay folds longer headers, and some clients then show them garbled), pointing to MAIL-71.
- `notify/settings.py`, `MIN_HOURS_BETWEEN_DIGESTS`: comment that the gap exists to stop digest floods on busy projects, pointing to NOTIF-9. The existing line is unchanged.

Needs your decision:
- The doc says `due()` holds a user's next digest for 24 hours. The code sets `MIN_HOURS_BETWEEN_DIGESTS = 6`. I recorded only the current value of 6 and did not reuse the 24-hour reason. Nothing I was given says why the value changed. Could you tell me the reason, or confirm 6 is right?

Not moved:
- The mail-provider incident note (pause sending from the provider dashboard, ask #mail-ops first) describes an operational step, not code behaviour, so it does not belong in code comments. It fits better in `docs/oncall.md`. I left that file unchanged; say if you want it moved there.
- `docs/digests.md` is still in place. Once the mail-ops note has a new home, it can be deleted.
- The digest scheduling code is not in this repository, so the ordering note sits on `build_digest()`, where the code relies on it.
