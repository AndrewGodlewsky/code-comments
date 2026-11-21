## Review of mig-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short overview and a Terms section defining outbox, drainer, tombstone, fence and version rule before they are used
- Explained how a fence actually works (share lock by writers, UPDATE waits for them) instead of only describing the effect
- Replaced the unexplained terms 'follower' and 'SoT' with plain definitions and consistent use
- Stated which database the drainer polls (the current SoT) and how it retries, moved the drainer behaviour into step 2 in a clearer order
- Made step 4's trigger condition explicit and tied the 2-minute wait to its reason
- Clarified the step 9 precondition about reverse-direction code paths and the pause arithmetic
- Added a State line to the rollback step and reordered fields consistently (Starts, Changes, State, If it fails)
- Rewrote step 11's failure note to say why mirror=both is only safe before the first unmirrored create or update
- Shortened sentences throughout and removed repetition without changing any decision
- Rewrote the intro to state the shared mechanism as three parts: write plus outbox row, best-effort inline copy, drainer repair.
- Defined the follower, and added a Flags term describing the 30-second cache.
- Clarified that the fence applies to SoT writes only, not to follower copies.
- Clarified the fail-closed meaning of the replica-lag check and what the circuit breaker does.
- Gave one-line meanings for each flag.
- Fixed an inaccurate claim: the switch pause was called 'well under 90 seconds' with a 60s deadline plus 30s flag refresh, which can reach 90. Lowered the deadline to 45s (watchdog 60s) so the worst case is 75s, and gave rollback the same deadline.
- Reworded the step 9 precondition: the reverse-direction code is deployed in step 2, so it now says it must work instead of implying a later deploy.
- Clarified rollback step 5 (mirror=both makes Postgres the follower again) and the wait in step 4.
- Reflowed several dense bullets into short sub-bullets, and renamed 'flag flips' to 'flags change'.
- Rewrote the overview to explain the SoT/follower roles and the three-part write (commit with outbox row, quick copy, drainer repair) up front, with plain definitions.
- Terms: defined outbox, drainer, tombstone, version rule, fence and flags before use; explained that a fence uses a shared lock for writes and an exclusive lock to close, and that flags refresh every 30 seconds.
- Replaced 'forward/reverse outbox' with 'MySQL outbox'/'Postgres outbox' so the reader does not have to infer direction.
- Added `switch_state` to the step 1 schema list, since step 9 relies on it.
- Step 2: noted that the reverse-direction paths are deployed here and that all processes export app_flag_value.
- Step 9: numbered the sub-steps and referenced them as sub-steps elsewhere; replaced the vague 'reverse-direction code paths work' with 'have been tested'; clarified that the clean abort is because nothing was written to Postgres as SoT.
- Step 11: clarified the failure case and when rollback is no longer safe.
- Replaced jargon such as 'inline copy' and 'delta comparison' with plainer descriptions; kept the checklist format, numbering and all requirements and numbers.

### Holes
- None.
