import unittest

from auth import settings
from auth.forms import save_form
from auth.lockout import Lockout
from auth.reset import link_is_valid
from auth.sessions import SessionStore
from auth.views import sign_in


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class SessionTest(unittest.TestCase):
    def test_session_survives_up_to_the_ttl(self):
        clock = Clock()
        store = SessionStore(clock)
        sid = store.start("ada")
        clock.now += settings.SESSION_TTL_S
        self.assertTrue(store.touch(sid))

    def test_session_ends_after_the_ttl(self):
        clock = Clock()
        store = SessionStore(clock)
        sid = store.start("ada")
        clock.now += settings.SESSION_TTL_S + 1
        self.assertFalse(store.touch(sid))

    def test_banner_shows_near_the_end(self):
        clock = Clock()
        store = SessionStore(clock)
        sid = store.start("ada")
        clock.now += settings.SESSION_TTL_S - settings.IDLE_WARNING_S - 1
        self.assertFalse(store.should_warn(sid))
        clock.now += 1
        self.assertTrue(store.should_warn(sid))

    def test_form_is_not_saved_after_the_session_ends(self):
        clock, saved = Clock(), []
        store = SessionStore(clock)
        sid = store.start("ada")
        self.assertTrue(save_form(store, sid, {"name": "Ada"}, saved))
        clock.now += settings.SESSION_TTL_S + 1
        self.assertFalse(save_form(store, sid, {"name": "Ada L."}, saved))
        self.assertEqual(saved, [{"name": "Ada"}])


class SignInTest(unittest.TestCase):
    def test_lockout_after_max_failures(self):
        store, lockout = SessionStore(Clock()), Lockout()
        for _ in range(settings.MAX_FAILED_LOGINS):
            sign_in(store, lockout, "ada", password_ok=False)
        self.assertIsNone(sign_in(store, lockout, "ada", password_ok=True))

    def test_reset_link_expires(self):
        self.assertTrue(link_is_valid(0, now=settings.RESET_LINK_TTL_S))
        self.assertFalse(link_is_valid(0, now=settings.RESET_LINK_TTL_S + 1))


if __name__ == "__main__":
    unittest.main()
