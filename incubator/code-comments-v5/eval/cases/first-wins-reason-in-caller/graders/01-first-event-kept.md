---
type: llm
focus: core
weight: 2
---

Hidden tests: with repeated users, one_login_per_user keeps exactly one event per user, and it is that user's first event, so the trial clock in billing/trial_clock.sql starts at each user's first login.
