import unittest

from museum.guestbook import guestbook_html
from museum.store import CommentStore


class GuestbookTest(unittest.TestCase):
    def test_the_newest_comment_comes_first(self):
        store = CommentStore()
        store.add("bee-01", 1, "Saw the queen")
        store.add("bee-01", 2, "Loud in here")
        page = guestbook_html(store, "bee-01")
        self.assertLess(page.index("Loud in here"), page.index("Saw the queen"))

    def test_comments_from_other_exhibits_are_left_out(self):
        store = CommentStore()
        store.add("moth-04", 1, "Huge wings")
        self.assertNotIn("Huge wings", guestbook_html(store, "bee-01"))


if __name__ == "__main__":
    unittest.main()
