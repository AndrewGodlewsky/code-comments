The runner now lets up to 8 jobs run in parallel instead of 4.

The change is one line: `MAX_PARALLEL` in `jobs/limits.py` went from 4 to 8. `run_all` sizes its thread pool from that value, and `docs/operations.md` points to it, so nothing else needed editing. The existing concurrency test uses the same constant, so it follows the new cap. I did not run the tests.

I left the 0.4.0 entry in `CHANGELOG.md` ("up to 4 at a time") and the 2026-09-02 capacity report alone. Both describe the past, and the report notes the host could take more parallel jobs. If you want a changelog line for this change, I can add one.
