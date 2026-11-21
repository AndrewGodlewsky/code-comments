# Users migration plan

- [ ] Create the new tables in Postgres and MySQL (users, tombstones, pending, backfill progress)
- [ ] Deploy the updated UserRepository, sweepers and comparer
- [ ] Turn on dual writes via `users.write_mode`
- [ ] Run the backfill from the replica (2k batches, respect replica lag)
- [ ] Run the comparer until it's clean
- [ ] Ramp `users.read_from_pg` 1/10/50/100, keep it at 100% for 3 days
- [ ] Freeze writes, restart the Postgres id sequence, switch `write_mode` to Postgres primary
- [ ] Keep MySQL in sync for 14 days (rollback still possible)
- [ ] Switch to `pg_only`, then back up and drop the MySQL table
