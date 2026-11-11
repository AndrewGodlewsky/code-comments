Done. I changed `MAX_PARALLEL` from 4 to 8 in `jobs/limits.py`. The tests pass.

I did not edit any comments or docs. Nothing else hard-codes the old number, and the comments in `jobs/limits.py` and `jobs/runner.py` and the text in `docs/operations.md` refer to `MAX_PARALLEL` by name, so they are still true.

- `CHANGELOG.md` still says "Jobs run up to 4 at a time" under 0.4.0. That entry records a past release, so I left it. If you want a release note for this change, add a new entry when you cut the version.
- The 2026-09-02 capacity report measured only 4 parallel jobs (38 minutes, CPU peaking at 61%). It says nothing about 8, so it doesn't show that 8 is safe on the refreshed host. If you want the reason for 8 written next to the constant, give me the figures and I'll add them.
