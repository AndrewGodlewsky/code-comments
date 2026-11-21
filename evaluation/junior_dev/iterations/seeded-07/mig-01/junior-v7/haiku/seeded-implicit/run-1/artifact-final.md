# Users migration plan

This moves the `users` table from MySQL 8 to Postgres 16 while the service keeps running. Today `UserRepository` reads from the MySQL replica and writes to the MySQL primary. The plan first copies every write to Postgres, then copies the existing rows, then compares the two tables, then moves reads to Postgres in steps, and only then makes Postgres the source of truth. Every change commits in its source database together with a pending row, and every copy follows one version rule, so copies can repeat and race safely.

## Terms

- **Source of truth**: the database whose row wins when the two disagree. Each change commits there first.
- **Target**: the other database. Changes are copied there after they commit.
- **Replica**: a read-only copy of MySQL that serves reads. **Replica lag** is how far behind it is. It is exported as `mysql_replica_lag_seconds`.
- **version**: an integer column on `users`. It starts at 1 on create, and the source adds 1 on every update. Copies keep the source's number.
- **Version rule**: a copy inserts a row that is missing, or replaces an existing row only if that row's `version` is lower than the incoming one.
- **Pending table**: a table `pending` in each database. A pending row asks for one user to be copied to the other database, or deleted there. It is written in the same transaction as the change, so a crash cannot lose it. A pending row sits in the pending table of the database that holds the change's source. It has an id, a user id, an op (`copy` or `delete`) and a creation time.
- **Tombstone**: a row in the `tombstones` table of each database that records a deleted user id. A copy never writes a user whose id has a tombstone in the target database.
- **Sweeper**: a loop in each worker process that works through pending rows. It is not a `jobs` job, because a job that fails five times goes to `jobs:dead`, where nothing retries it.
- **Comparer**: a loop that reads both tables and reports rows that differ.
- **Backfill**: a one-time copy of the whole table from the replica into Postgres.
- **Advisory lock**: a short lock on one user id, taken on the target during a copy or a delete, so a copy and a delete of the same user cannot interleave. Postgres: `pg_advisory_xact_lock`. MySQL: `GET_LOCK`.
- **Id sequence**: the counter that gives each new user its id. MySQL calls it `AUTO_INCREMENT`. Postgres calls it a sequence.
- **Retryable 503**: an HTTP error that tells the client to try the request again later.
- **`users.write_mode`** (flag): which database is the source of truth for writes.
  - `mysql_only`: before the migration. Also the value when the flag is unset.
  - `mysql_primary`: dual write. MySQL is the source, and each write is copied to Postgres.
  - `pg_primary`: Postgres is the source, and each write is copied to MySQL.
  - `pg_only`: Postgres only. Nothing is copied to MySQL.
  - `frozen`: every write returns a retryable 503. Reads still work. Used only during a switch or a rollback.
- **`users.read_from_pg`** (flag): a percentage, 0 to 100, of users whose reads go to Postgres. `flags.enabled_for(name, key)` gives the same answer for the same key every time, so a given user always lands on the same side.
- Flags are cached in each app instance for 30 seconds. The metric `app_flag_value{flag=...}` shows the value each instance is using.
- **Freeze**: setting `frozen` and waiting until every instance shows it.
- **Clean pass**: one full comparer pass with zero confirmed mismatches.
- **Confirmed mismatch**: a difference the comparer still sees 60 seconds after it first finds it.

## How the system runs

### Writes in mysql_primary

Starts: a create, update or delete reaches `UserRepository` while the mode is `mysql_primary`.

1. The change and a pending row are written in one MySQL transaction, then committed. If that fails, the request fails, as it does today. A delete also writes a tombstone in MySQL, in the same transaction. `UserRepository.delete` is the only delete path, so every user delete leaves a tombstone.
2. After the commit, the repository copies the change to Postgres under the version rule, holding the advisory lock on the user id. The copy writes every column of the row. For a delete, the copy does what the sweeper's delete row does: it writes the tombstone to Postgres, then deletes the Postgres row. The copy waits at most 200 ms.
3. If the copy works, the pending row is deleted. If the copy fails or times out, the request still succeeds and the pending row stays for the sweeper. If the copy works but the pending row cannot be deleted, the row stays and the sweeper repeats the copy, which the version rule makes harmless. In this mode a Postgres failure never fails the request.

State: the change, the tombstone and the pending row are in MySQL. The copy lands in Postgres.

### Writes in pg_primary

The same steps with the roles swapped. Postgres is written first, with its pending row in the Postgres `pending` table. MySQL is the target. A Postgres failure fails the request, because Postgres is then the source.

### Ids

In `mysql_primary`, MySQL assigns the id on create, and the copy to Postgres keeps it. In `pg_primary`, Postgres assigns the id from its sequence, and the copy to MySQL keeps it. Each user has one id on both sides.

### Sweeper

Starts: every worker runs the sweeper every 10 seconds.

The sweeper runs in every mode and never reads the mode. Each run drains both pending tables. A row in MySQL's `pending` is copied to Postgres. A row in Postgres's `pending` is copied to MySQL. The table a row sits in gives its direction, so a change of mode does not change how the sweeper works. Each run takes up to 100 rows from each table, oldest first. Several workers may run it at once, and repeats are harmless.

- Rows are not merged. Each row is handled on its own. A copy row reads the current source row, so the order of rows for one user does not change the result. A copy that finds no source row only deletes its pending row. A delete row blocks later copies with its tombstone.
- **Copy row**: reads the current row from the source primary and copies it under the version rule, holding the advisory lock. If the row is gone, it only deletes the pending row.
- **Delete row**: writes the tombstone to the target, then deletes the target row. Both steps are safe to repeat. An existing tombstone and a missing row change nothing.
- On success the pending row is deleted. On failure it stays and is retried on the next tick. A crash during a run leaves the pending row in place, so it is retried.

This is how anything the other database missed is repaired, with no manual step.

### Backfill

Starts: automatically, once every instance reports `mysql_primary`. Before that, a write from an older instance could be missed.

Each batch:

1. If replica lag is above 5 seconds, wait and check again. Reporting jobs share the replica.
2. Read up to 2,000 rows from the replica, with an id above the saved last id, in id order.
3. In one Postgres transaction, copy each row (version rule, Postgres tombstone check, advisory lock) and save the batch's last id in `backfill_progress`.
4. Repeat until no rows remain. The backfill then ends.

`backfill_progress` lives in Postgres only, because it describes the Postgres side. After a crash the open batch rolls back, and the run continues after the last completed batch. A row changed by a dual write during the copy keeps its newer version. A user deleted after the replica read may be copied once. The delete's pending row then removes that copy, and the tombstone blocks any later copy.

### Comparer

Starts: automatically when the backfill ends. It runs full passes over both tables in id order until the MySQL table is dropped. It reads the replica with the same 5-second lag pause, compares every column including `version`, and skips ids that have a tombstone in either database.

- Each difference is checked again against both primaries 60 seconds later. A difference that remains is a confirmed mismatch.
- For each confirmed mismatch the comparer adds a pending copy row to the pending table of the current source: MySQL in `mysql_primary`, Postgres in `pg_primary`. The sweeper then repairs it. If a confirmed mismatch duplicates a pending row already waiting, the version rule makes the extra copy harmless.
- A row that differs only because a write is still in flight usually matches by the re-check, because the 200 ms copy or the sweeper's next tick has normally landed by then. A copy that still fails after 60 seconds is a real mismatch.
- During a freeze the comparer keeps reading and checking, but writes no pending rows. It writes them after the freeze ends.
- The result of each pass (start time, end time, confirmed mismatch count) is written to a `comparer_runs` table in Postgres. The switch to Postgres reads the latest completed pass here. A pass still running has no end time yet.

### Reads

For each request, `flags.enabled_for("users.read_from_pg", user_id)` picks the side. A selected user reads Postgres. If that read fails or takes longer than 200 ms, the request reads the MySQL replica instead, so reads never fail. Everyone else reads the MySQL replica, as today. A Postgres row may trail a write by a moment, as the replica already does. Changing the read percentage does not change where writes go.

### Freezes and switches

Any change of source of truth uses a freeze. Writes are paused so that no write lands on the old side during the change. Paused writes get a retryable 503, which the clients already retry. Reads keep working. A person runs each switch and each rollback by setting the flags, and checks the limits below.

1. Set `users.write_mode` to `frozen`. Each instance sees it within 30 seconds. Writes already running finish within their 5-second write timeout.
2. Wait until the metric shows `frozen` on every instance, within 40 seconds of step 1. If it does not, set the old mode back and try later. Nothing has changed yet.
3. Do the switch work for this change, then set the new mode.
4. Wait until the metric shows the new mode on every instance.

The switch work must finish within 15 seconds. Writes are paused for at most 40 + 15 + 30 = 85 seconds, under the 90-second limit. If the switch work runs over, set the old mode back and try later. The person running the switch measures these limits. The brief does not say whether a tool enforces them.

Switch work to Postgres:

- **Drain**: the MySQL `pending` table should already be empty, because checklist step 8 requires it. No new rows arrive while frozen, apart from writes that were already in flight. The sweeper runs every 10 seconds and takes up to 100 rows per run, so a few leftover rows drain within one or two runs. The drain is done when a query of the MySQL primary's `pending` table returns zero rows. The primary is checked, not the replica, because the replica may lag. If the drain is not done within the 15 seconds, the switch fails.
- **Ids**: read MySQL's `AUTO_INCREMENT` counter and set the Postgres id sequence so its next id is that number, or the sequence's current next id if that is higher. MySQL has issued only lower ids, so Postgres cannot reuse one. Gaps are fine. The sequence never moves backwards.

## Rollout checklist

- [ ] **1. Create the tables.**
  - Starts: a migration run, by the team.
  - Changes: creates `users`, `tombstones` and `pending` in MySQL (`core`) and in Postgres. Creates `backfill_progress` and `comparer_runs` in Postgres only.
  - State: the databases. Nothing reads these tables yet.
  - If it fails: run it again. No user is affected.

- [ ] **2. Deploy the new `UserRepository`, sweeper and comparer.**
  - Starts: a deploy.
  - Changes: code only. With the flag unset the mode is `mysql_only`, so behaviour matches today and nothing is copied.
  - If it fails: roll back the deploy.

- [ ] **3. Turn on dual writes.**
  - Starts: a person sets `users.write_mode` to `mysql_primary`.
  - Changes: every write is also copied to Postgres.
  - State: the flag.
  - Wait until `app_flag_value{flag="users.write_mode"}` shows `mysql_primary` on every instance.
  - If it fails: backfill does not start. Writes from an instance still on `mysql_only` are in MySQL, and the backfill copies them later.

- [ ] **4. Run the backfill.**
  - Starts: automatically, once every instance shows `mysql_primary`.
  - Changes: copies `users` from the replica to Postgres in id order, 2,000 rows per batch, pausing when lag is above 5 seconds.
  - State: `backfill_progress` in Postgres.
  - If it fails: it continues after the last completed batch. It ends when no rows remain.

- [ ] **5. Run the comparer until it is clean.**
  - Starts: automatically, after step 4 ends. Passes repeat.
  - Changes: confirmed mismatches are repaired through pending rows.
  - State: the pending tables and `comparer_runs`.
  - Clean means one full pass with zero confirmed mismatches. Do not ramp reads before that.
  - If it fails: a mismatch that persists is repaired by the next pass. See the failure table.

- [ ] **6. Ramp `users.read_from_pg`.**
  - Starts: a person sets the flag to 1, then 10, then 50, then 100. Before each next step, wait for a clean pass in `comparer_runs`.
  - Changes: which side selected users read from. Writes are not affected.
  - State: the flag.
  - Watch: Postgres read errors and fallbacks, read latency, pending backlog on both sides, and comparer mismatches.
  - If something looks wrong: set the flag to 0. Reads return to MySQL at once.

- [ ] **7. Keep reads at 100% for 3 days.**
  - Starts: when every instance shows 100.
  - If the flag drops below 100, the 3 days start again from the next time it is 100.
  - The comparer keeps running.

- [ ] **8. Switch the source of truth to Postgres.**
  - Starts: a person, when all of these hold: reads have been at 100% for 3 days, the latest completed pass in `comparer_runs` is clean, and MySQL pending is empty. The person checks pending with a query of the MySQL primary, not the replica. A pass that is still running does not count, so the person waits for it to finish.
  - Changes: a freeze, then the switch work (drain MySQL pending to zero, set the Postgres id sequence), then `pg_primary`. From then on, Postgres assigns ids and each write is copied to MySQL.
  - State: the flag, the Postgres sequence and the pending tables.
  - If it fails: if the freeze does not reach every instance in time, or the switch work runs over 15 seconds, set the old mode back and try later.

- [ ] **9. Keep MySQL in sync for 14 days.**
  - Starts: when step 8 is done.
  - Changes: nothing new. Writes go to Postgres first and are copied to MySQL by the sweeper. The comparer keeps checking.
  - State: the pending tables.
  - If it fails: the sweeper retries failed copies. Rollback is possible throughout (see Rollback to MySQL).

- [ ] **10. Switch writes to Postgres only.**
  - Starts: a person, at least 14 days after step 8, when Postgres pending is empty and the latest completed pass in `comparer_runs` is clean.
  - Changes: set `users.write_mode` to `pg_only`. MySQL stops receiving copies. No freeze is needed, because Postgres is already the source. Wait until the metric shows `pg_only` on every instance.
  - Then: back up MySQL `users`, `tombstones` and `pending`, and drop the MySQL `users` table, with its tombstones and pending rows.
  - State: the flag, and the backup.
  - If it fails: if the backup fails, drop nothing.
  - After this step, rollback to MySQL is no longer possible.

- [ ] **11. Remove the MySQL code paths.**
  - Starts: after step 10.
  - Changes: a deploy that removes the MySQL branches and the flags.
  - If it fails: roll back the deploy. The data is not changed by this step. See Open questions.

## Rollback to MySQL (any time before step 10)

A person runs these steps. Steps 2 to 4 use the freeze rules, and the switch work must finish within 15 seconds.

1. Set `users.read_from_pg` to 0. Reads return to MySQL, which has every write.
2. Freeze (`frozen`) and wait for the metric.
3. Drain Postgres pending to zero, so MySQL has every write. The sweeper does this while frozen: it copies Postgres `pending` rows to MySQL whatever the mode is. The check is a query of the Postgres primary's `pending` table.
4. Check that MySQL's `AUTO_INCREMENT` is above every user id on either side. Each copy into MySQL inserts its id explicitly, which moves the counter past that id, so this normally holds. If it does not, set the counter above the highest id before continuing.
5. Set `users.write_mode` to `mysql_primary`, and wait for the metric.

Only the two flags change, plus MySQL's counter if step 4 had to raise it. Postgres keeps its rows, and copies continue in the other direction. After a rollback, steps 6 and 7 must run again.

## What happens when things fail

| Failure | What happens |
|---|---|
| Postgres down or slow in `mysql_primary` | Requests succeed. Pending rows build up in MySQL. The sweeper copies them when Postgres is back. |
| Postgres down in `pg_primary` | Writes fail, because Postgres is the source. Reads fall back to MySQL. |
| MySQL primary down in `mysql_primary` | Writes fail, as today. Replica reads continue. The sweeper waits. |
| Postgres read fails or takes longer than 200 ms | That request reads the MySQL replica instead. |
| Copy finds the target row has the same or a higher version | Nothing changes. The pending row is deleted. A higher target version means a bug, so the comparer keeps reporting it. |
| Copy finds the target row has the same version but different content | Nothing changes. Equal versions should not happen, because only the source numbers writes. The comparer reports it as a mismatch. |
| Copy refused because another row holds the same email | The copy writes every column, including email. Email is unique in each database, so the refusal happens on the target, where a different row holds the email. The pending row stays and is retried. The other user's own copy usually frees the email. If it never does, see Open questions. |
| Replica lag above 5 seconds | Backfill and comparer pause. Reads and writes are not affected. |
| Crash during backfill | The open batch rolls back. The run continues after the last completed batch. |
| Crash during the sweeper | The pending row stays and is retried. |
| Flag does not reach every instance | Backfill does not start, and switches wait for the metric. |
| Copy and delete of the same user race | The advisory lock and the tombstone keep the user deleted. |
| Freeze does not reach every instance in 40 seconds, or switch work runs over 15 seconds, or MySQL pending is not zero in time | Set the old mode back and try later. Nothing has been switched. |
| Comparer during a freeze | Keeps reading and checking. Writes its pending rows after the freeze ends. |

## Open questions

- Who may change `users.write_mode` and `users.read_from_pg`? The brief does not say.
- Is the person running a switch also the one who enforces the 40 s, 15 s and 90 s limits, or does a tool? The brief does not say.
- If another user's email clash never clears, should the copy keep retrying, or is there a rule to follow? The brief requires no manual fix.
- If a backfill batch always fails on one bad row, should it skip the row or stop?
- How long is the MySQL backup kept after the drop?
- The numbers used here (200 ms copy and read timeouts, 5 s write timeout, 10 s sweeper interval, 60 s re-check, 40 s freeze check, 15 s switch work) are starting values. They need checking under load.
- How long should each ramp step be held beyond a clean comparer pass? The brief does not say.
- What does the code from before step 11 do if `users.write_mode` is `pg_only`? If a rollback of that deploy is needed, the old code must not write to MySQL.
- In `pg_only` MySQL gets no copies, so the comparer would report every row that differs from it. Does the comparer stop at step 10 when the MySQL table is dropped, or earlier?
