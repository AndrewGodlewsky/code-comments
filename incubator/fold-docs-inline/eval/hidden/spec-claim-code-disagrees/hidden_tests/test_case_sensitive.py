import unittest

from accounts.users import Directory


class CaseTest(unittest.TestCase):
    def test_lookup_is_exact(self):
        directory = Directory()
        directory.register("ann")
        self.assertIsNone(directory.find_user("Ann"))
        self.assertIsNotNone(directory.find_user(" ann "))

    def test_names_differing_in_case_are_separate_accounts(self):
        directory = Directory()
        directory.register("ann")
        directory.register("Ann")
        self.assertEqual(directory.find_user("Ann")["name"], "Ann")
