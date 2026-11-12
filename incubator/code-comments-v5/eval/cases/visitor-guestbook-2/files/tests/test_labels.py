import unittest

from museum.labels import Exhibit, label_html


class LabelTest(unittest.TestCase):
    def test_an_ampersand_in_a_note_shows_as_typed(self):
        wasp = Exhibit("wasp-02", "Paper wasp", "Nests of chewed wood & saliva.")
        self.assertIn("Nests of chewed wood &amp; saliva.", label_html(wasp))

    def test_a_long_note_keeps_its_line_breaks(self):
        moth = Exhibit("moth-04", "Atlas moth", "Wingspan up to 25 cm.\nAdults never feed.")
        self.assertIn("Wingspan up to 25 cm.<br>Adults never feed.", label_html(moth))


if __name__ == "__main__":
    unittest.main()
