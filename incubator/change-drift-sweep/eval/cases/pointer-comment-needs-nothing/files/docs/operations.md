# Operating the job runner

The runner never runs more jobs at once than `MAX_PARALLEL` in `jobs/limits.py`.
A job that keeps failing is tried four times, then marked failed.
The status dashboard refreshes every four seconds.
