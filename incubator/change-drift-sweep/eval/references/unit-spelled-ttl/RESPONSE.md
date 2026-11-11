The idle session timeout is now 30 minutes: `SESSION_TTL_S` in `auth/settings.py` went
from 900 to 1800 seconds.

Updated the places that described the old timeout: the `auth/sessions.py` module
docstring, the `sign_in` docstring in `auth/views.py`, the idle-session line in
`docs/security.md`, and the `auth/forms.py` docstring, which gave it as "a quarter of an
hour". `docs/console.md` said the "Still there?" banner appears after 14 minutes; the
banner comes `IDLE_WARNING_S` (60 s) before the end, so it now appears after 29 minutes.

Left alone because they describe other things that also use 15 minutes: password-reset
links (`RESET_LINK_TTL_S`), the lockout after 15 failed sign-ins, and the identity
provider's 15-minute access tokens, which the identity team sets.

The tests pass.
