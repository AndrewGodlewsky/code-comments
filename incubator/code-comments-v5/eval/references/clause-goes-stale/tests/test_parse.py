import unittest

from tags.parse import parse_tags
from tags.search import tag_filter


class ParseTagsTest(unittest.TestCase):
    def test_splits_and_normalises(self):
        self.assertEqual(parse_tags("Red, blue,red"), ["red", "blue"])

    def test_blank_text_raises(self):
        with self.assertRaises(ValueError):
            parse_tags(" , ")


class TagFilterTest(unittest.TestCase):
    def test_no_parameter_means_no_filter(self):
        self.assertIsNone(tag_filter({}))

    def test_parameter_is_parsed(self):
        self.assertEqual(tag_filter({"tags": "a,b"}), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
