# ADR 0002: Incremental export with --since

- Status: accepted
- Date: 2026-05-28

## Context

The nightly job exported every order row, about two million a night, and took 40 minutes.
Most rows had not changed since the night before.

## Decision

`reportctl export` takes `--since DATE` and writes only rows whose `changed` date is on or after DATE.
The nightly job passes the date of its last successful run.

## Consequences

- A night's export is usually under 1% of the table.
- A missed night needs a backfill from the first missing day; see the backfill runbook.
