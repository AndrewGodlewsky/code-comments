## Review of cred-02 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short glossary up front (TOTP, step, sealed, recovery code, sid, challenge) so a reader outside the project can follow the terms.
- Explained the 'step' and the one-step-either-side window in plain words.
- Shortened the diagram labels and added explicit self-loops for wrong entries, so failure paths show in the diagram itself; the details stay in the table.
- Reworded the 'Challenge, wrong entry' row, which said 'an unused-looking code that is not valid' and was unclear.
- Made the 'no session until the second factor passes' rule explicit in the state-storage section.
- Explained why the challenge is a server-side row, and that the email send is retried in the background and never fails sign-in.
- Clarified the lost-phone and open-item wording without changing their meaning; the undecided support-reset path is still not designed.
- Added a plain opening paragraph explaining what changes: a correct password now yields a challenge, not a session.
- Added the terms 'active secret' and 'pending secret', expanded KMS, and explained what a challenge is and is not, in the terms section.
- Explained why a step is a 30-second window and why the server accepts neighbouring steps.
- Explained that sealed values are encrypted at rest and that recovery codes are stored as hashes only.
- In the state section, explained that the account's state is derived from which columns are set, and what last_used_step means.
- Explained in plain words why the challenge is a server-side row (atomic wrong-entry count) and how its cookie relates to sid.
- Reworded the transitions table for clarity, and spelled out the one-transaction steps (activate, replace codes, delete other sessions) in the setup and replacement rows.
- Clarified the TOTP and recovery-code transition rows, including the conditional update and the claim-by-update for recovery codes.
- Open item 2: marked the password re-entry idea as a recommendation and explained why it still works for a lost phone.
- Open item 4: added a concrete example of the replay rule rejecting an unused older step.
- Diagram structure and labels were left unchanged, so the diagram means exactly what it did before.
- Opening: explained in plain words what the diagram shows (the 2FA lifecycle and one sign-in attempt) and what a challenge means for the session.
- Terms: expanded TOTP, sealed, and recovery code so a reader outside the project knows what RFC 6238, AES-GCM, KMS, and sha256 are used for. Added definitions for 'wrong entry' and why the pending secret is kept apart from the active one.
- Added a 'How to read the diagram' section that defines the four lifecycle states and says that sign-in runs as a separate attempt.
- Storage: stated that the lifecycle state is derived from which columns are set, and explained what the atomic update of the wrong-entry count protects against.
- Transitions table: reworded the trigger and failure cells in plain language. The rules are unchanged: the step check, conditional updates, 5-attempt and 5-minute limits, and the email rules.
- Open items: kept all six, reworded for clarity, and did not add any design decisions.

### Holes
- None.
