Set `MAX_PARALLEL` in `jobs/limits.py` to 8, so up to 8 jobs now run at once.

Nothing else needed changing. The comments and `docs/operations.md` refer to
`MAX_PARALLEL` by name, not by its value. The other 4s in the repository are
`MAX_TRIES`, the dashboard refresh, or records (the 0.4.0 CHANGELOG entry and the
2 September capacity report).

The tests pass.
