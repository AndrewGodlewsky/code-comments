The runner now allows up to 8 jobs in parallel. I changed `MAX_PARALLEL` from 4 to 8 in `jobs/limits.py`. `run_all` sizes its thread pool from that value, so no other code changed.

The existing comment on `MAX_PARALLEL` ("Upper bound on jobs running at once") is still true, so I left it as written. I did not add a comment recording the hardware refresh as the reason for 8. That is your reason, but the repository has no ticket or doc that states it, so I kept the comment to the value.

The unit tests pass (`python -m unittest`, 3 tests). The concurrency test checks that the peak never exceeds the cap. It does not show that the host can sustain 8 jobs. The 2026-09-02 capacity report only says the host "can take more parallel jobs after its hardware refresh". If you want confidence in 8, a timed run of the nightly batch would show it.

Two items I did not change:
- `CHANGELOG.md` has no entry for this change. The 0.4.0 line "Jobs run up to 4 at a time" is accurate history, so I did not edit it. A new changelog entry for the cap of 8 would be a reasonable follow-up.
- `docs/operations.md` refers to `MAX_PARALLEL` by name, not by its value, so it stays correct.
