## Review of auth-03 (simplify-only, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a short summary that says how the existing system works today, then a terms section with one line per term.
- Kept the components diagram and the three sequence diagrams in diagram form, and moved the notes under each diagram into numbered steps.
- Reduced each flow to numbered steps that say what happens. The lock and coordination notes now sit in the step that uses the lock, and the separate Coordination section is gone.
- Moved the failure-handling detail into one failure table. Kept every failure row from the original, with shorter wording.
- Merged the Data, Retention, Clock and Token bullets into one Stored data section.
- Merged the logging, referrer, fragment and queue-secret rules into one Secrets and logs section.
- Turned the reload-after-clear risk into a stated trade-off in Flow 2, since it is decided and not open.
- Cut the six risk items to four open questions. The raw-token queue risk moved into the components notes and secrets section. The logging risk moved into secrets and logs.
- No behaviour changed. Every fixed requirement from the brief is still in the design.

### Holes
- None.
