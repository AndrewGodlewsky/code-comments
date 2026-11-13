import unittest

from auth import settings
from auth.lockout import Lockout
from auth.reset import link_is_valid
from auth.sessions import SessionStore


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class IdleTimeoutTest(unittest.TestCase):
    def test_idle_timeout_is_thirty_minutes(self):
        self.assertEqual(settings.SESSION_TTL_S, 1800)

    def test_twenty_idle_minutes_keep_the_session(self):
        clock = Clock()
        store = SessionStore(clock)
        sid = store.start("ada")
        clock.now += 20 * 60
        self.assertTrue(store.touch(sid))

    def test_thirty_one_idle_minutes_end_it(self):
        clock = Clock()
        store = SessionStore(clock)
        sid = store.start("ada")
        clock.now += 31 * 60
        self.assertFalse(store.touch(sid))


class OtherLimitsUnchangedTest(unittest.TestCase):
    def test_reset_links_still_last_fifteen_minutes(self):
        self.assertEqual(settings.RESET_LINK_TTL_S, 900)
        self.assertFalse(link_is_valid(0, now=901))

    def test_lockout_still_after_fifteen_failures(self):
        self.assertEqual(settings.MAX_FAILED_LOGINS, 15)
        lockout = Lockout()
        for _ in range(14):
            lockout.record_failure("ada")
        self.assertFalse(lockout.is_locked("ada"))


class BannerTest(unittest.TestCase):
    def test_banner_shows_at_twenty_nine_minutes(self):
        self.assertEqual(settings.IDLE_WARNING_S, 60)
        clock = Clock()
        store = SessionStore(clock)
        sid = store.start("ada")
        clock.now += 29 * 60 - 1
        self.assertFalse(store.should_warn(sid))
        clock.now += 1
        self.assertTrue(store.should_warn(sid))
