"""The digest e-mail."""

# The company mail relay folds longer subject headers, and some mail clients then show
# the subject garbled (MAIL-71).
SUBJECT_LIMIT = 78


def subject(user_name, count):
    text = f"{user_name}, you have {count} unread notifications"
    return text if len(text) <= SUBJECT_LIMIT else text[: SUBJECT_LIMIT - 3] + "..."
