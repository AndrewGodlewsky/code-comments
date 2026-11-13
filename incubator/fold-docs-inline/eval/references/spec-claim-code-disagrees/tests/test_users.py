import unittest

from accounts.users import Directory, NameTaken


class DirectoryTest(unittest.TestCase):
    def test_register_and_find(self):
        directory = Directory()
        directory.register(" kim ")
        self.assertEqual(directory.find_user("kim")["role"], "member")

    def test_a_name_can_only_be_taken_once(self):
        directory = Directory()
        directory.register("kim")
        with self.assertRaises(NameTaken):
            directory.register("kim")

    def test_only_admins_grant_editor(self):
        directory = Directory()
        directory.register("kim")
        with self.assertRaises(PermissionError):
            directory.grant_role({"role": "member"}, "kim", "editor")
        directory.grant_role({"role": "admin"}, "kim", "editor")
        self.assertEqual(directory.find_user("kim")["role"], "editor")


if __name__ == "__main__":
    unittest.main()
