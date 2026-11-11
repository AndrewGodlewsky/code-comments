-- Each account's activation date and the end of its free trial.
-- user_logins holds one row per user, written by accounts/export.py from
-- one_login_per_user, and that row must be the user's FIRST login: it is the
-- activation date and starts the 14-day trial clock, and a later login must
-- never move it.
CREATE VIEW trial_clock AS
SELECT user,
       at AS activated_at,
       datetime(at, '+14 days') AS trial_ends
FROM user_logins;
