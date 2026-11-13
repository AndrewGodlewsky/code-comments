import unittest

from museum.labels import Exhibit, label_html


class LabelTest(unittest.TestCase):
    def test_latin_names_keep_their_italics(self):
        bee = Exhibit("bee-01", "Western honey bee", "A working colony of <em>Apis mellifera</em>.")
        self.assertIn("<em>Apis mellifera</em>", label_html(bee))

    def test_a_long_note_keeps_its_line_breaks(self):
        moth = Exhibit("moth-04", "Atlas moth", "Wingspan up to 25 cm.\nAdults never feed.")
        self.assertIn("Wingspan up to 25 cm.<br>Adults never feed.", label_html(moth))


if __name__ == "__main__":
    unittest.main()
