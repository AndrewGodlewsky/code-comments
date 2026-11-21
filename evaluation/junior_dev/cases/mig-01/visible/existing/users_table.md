# users table (MySQL 8, database `core`)

| column     | type                  | notes                           |
|------------|-----------------------|---------------------------------|
| id         | BIGINT AUTO_INCREMENT | primary key; current max ~41.2M |
| email      | VARCHAR(320)          | unique                          |
| name       | VARCHAR(200)          |                                 |
| plan       | VARCHAR(20)           | free / pro / team               |
| version    | INT                   | starts at 1, +1 on every update |
| updated_at | DATETIME(3)           | set by the repository           |

- About 38 million rows (ids have gaps left by deletions).
- Peak load: ~3,000 reads/s, ~400 writes/s.
- Rows are hard-deleted by the GDPR erasure job (~2,000 per day). There is
  no soft-delete column.
- One primary (`mysql-core-primary`) and one read replica
  (`mysql-core-replica`). Reporting jobs also use the replica; its lag is
  exported as the metric `mysql_replica_lag_seconds`.
- The target Postgres 16 cluster (`pg-core`) is provisioned and empty. The
  app already holds a connection pool to it (`app.db.postgres`).
