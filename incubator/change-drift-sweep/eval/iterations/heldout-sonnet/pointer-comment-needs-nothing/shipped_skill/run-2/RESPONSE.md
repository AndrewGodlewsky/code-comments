I changed `MAX_PARALLEL` in `jobs/limits.py` from 4 to 8. `run_all` sizes its thread pool from that value, so up to 8 jobs now run at once. The tests pass.

I changed no comments or docs. Every comment and doc that mentions the cap refers to `MAX_PARALLEL` by name rather than quoting 4, so they are still accurate. I left the 0.4.0 changelog line ("up to 4 at a time") as it is, because it records what that release did.

The 2 September capacity report measured the host only at 4 parallel jobs (61% peak CPU). It did not test 8, so I'd check CPU on the first nightly batch. I didn't record a reason for the value 8 in the code, since no source gives one beyond your request.
