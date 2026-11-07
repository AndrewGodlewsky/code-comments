# Backend upgrade: completed 2026-10-01

All request traffic now goes to the upgraded backend. The legacy backend has been
decommissioned and nothing routes to it any more.

The upgraded backend accepts at most eight retries per request. Requests that ask
for more are rejected at the gateway, so clients should validate the same bound.
