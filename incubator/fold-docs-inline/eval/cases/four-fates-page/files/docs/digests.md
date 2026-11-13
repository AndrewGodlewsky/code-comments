# Notification digests

The digest job runs after the nightly notification cleanup, so a digest never includes
notifications that the cleanup removed.

- `build_digest()` groups a user's unread notifications by project.
- `due()` holds back a user's next digest until 24 hours after the last one, because
  users on busy projects complained about digest floods in the 2025 survey (NOTIF-9).
- Subjects are cut to `SUBJECT_LIMIT` (78) characters because the company mail relay folds
  longer subject headers, and some mail clients then show the subject garbled (MAIL-71).
- During a mail-provider incident, support pauses all sending from the provider's
  dashboard. Ask in #mail-ops before pausing.
