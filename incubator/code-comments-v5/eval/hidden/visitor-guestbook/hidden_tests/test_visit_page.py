import unittest

from museum.guestbook import guestbook_html
from museum.labels import Exhibit, label_html
from museum.store import CommentStore
from museum.visit_page import visit_page


def page_for(*texts):
    store = CommentStore()
    for posted_at, text in enumerate(texts):
        store.add("bee-01", posted_at, text)
    return guestbook_html(store, "bee-01")


class GuestbookShowsCommentsAsTypedTest(unittest.TestCase):
    def test_a_script_shows_as_text(self):
        page = page_for('<script>alert("hi")</script>')
        self.assertNotIn("<script", page.lower())
        self.assertIn("&lt;script&gt;", page)

    def test_tags_show_as_text(self):
        page = page_for("<b>best</b> room <img src=x onerror=alert(1)>")
        self.assertNotIn("<b>", page)
        self.assertNotIn("<img", page)
        self.assertIn("&lt;b&gt;best&lt;/b&gt; room", page)

    def test_an_ampersand_is_escaped_once(self):
        page = page_for("Bees & honey")
        self.assertIn("Bees &amp; honey", page)
        self.assertNotIn("&amp;amp;", page)

    def test_each_comment_is_a_caption_with_its_line_breaks(self):
        page = page_for("first visit", "second visit\nwith my class")
        self.assertIn('<ul class="guestbook">', page)
        self.assertEqual(page.count('<p class="caption">'), 2)
        self.assertIn("second visit<br>with my class", page)
        self.assertLess(page.index("second visit"), page.index("first visit"))


class LabelsKeepTheirMarkupTest(unittest.TestCase):
    def test_latin_names_stay_in_italics(self):
        ant = Exhibit("ant-02", "Leafcutter ants", "<em>Atta cephalotes</em> grow their own fungus.")
        self.assertIn("<em>Atta cephalotes</em> grow their own fungus.", label_html(ant))

    def test_the_visit_page_keeps_label_markup_and_escapes_comments(self):
        store = CommentStore()
        store.add("ant-02", 1, "<i>so</i> many ants")
        ant = Exhibit("ant-02", "Leafcutter ants", "<em>Atta cephalotes</em> at work.")
        page = visit_page(ant, store)
        self.assertIn("<em>Atta cephalotes</em> at work.", page)
        self.assertIn("&lt;i&gt;so&lt;/i&gt; many ants", page)
        self.assertNotIn("<i>", page)


if __name__ == "__main__":
    unittest.main()
