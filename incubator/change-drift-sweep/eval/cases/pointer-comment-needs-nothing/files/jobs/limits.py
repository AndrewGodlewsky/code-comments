"""Limits for the job runner."""

# Upper bound on jobs running at once; run_all sizes its pool from it.
MAX_PARALLEL = 4

# Tries per job, counting the first, before the job is marked failed.
MAX_TRIES = 4
