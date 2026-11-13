"""Security settings for the admin console."""

# Idle time, in seconds, after which a session ends.
SESSION_TTL_S = 1800

# Seconds before an idle session ends that the console shows its "Still there?" banner.
IDLE_WARNING_S = 60

# Lifetime of a password-reset link, in seconds.
RESET_LINK_TTL_S = 900

# Failed sign-ins in a row that lock an account.
MAX_FAILED_LOGINS = 15
