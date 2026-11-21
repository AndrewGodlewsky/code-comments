# user_repository.py -- the only code that reads or writes the `users` table.
# A lint rule (no-raw-users-sql) rejects SQL on `users` anywhere else.

from app.db import mysql          # mysql.primary, mysql.replica
from app.db import postgres       # pool to pg-core; unused so far
from app.flags import flags       # see flags_and_jobs.md
from app.jobs import jobs         # see flags_and_jobs.md


class StaleWrite(Exception):
    """Raised when the row's version changed since the caller read it."""


class UserRepository:
    def get(self, user_id):
        # Reads use the replica (lag is normally under 1 s).
        return mysql.replica.query_one(
            "SELECT * FROM users WHERE id = %s", user_id)

    def create(self, email, name, plan):
        with mysql.primary.transaction() as tx:
            user_id = tx.insert(
                "INSERT INTO users (email, name, plan, version, updated_at) "
                "VALUES (%s, %s, %s, 1, NOW(3))", email, name, plan)
        return user_id   # assigned by MySQL AUTO_INCREMENT

    def update(self, user_id, expected_version, **fields):
        # Optimistic locking: every successful update bumps version by 1.
        sets = ", ".join(f"{k} = %s" for k in fields)
        with mysql.primary.transaction() as tx:
            n = tx.execute(
                f"UPDATE users SET {sets}, version = version + 1, "
                "updated_at = NOW(3) WHERE id = %s AND version = %s",
                *fields.values(), user_id, expected_version)
        if n == 0:
            raise StaleWrite(user_id)

    def delete(self, user_id):
        # Hard delete. Only called by the GDPR erasure job.
        with mysql.primary.transaction() as tx:
            tx.execute("DELETE FROM users WHERE id = %s", user_id)
