import unittest
from ais.wake_word import is_wake_phrase


class TestWakeWord(unittest.TestCase):
    def test_exact_phrase(self):
        self.assertTrue(is_wake_phrase("Hey Rex"))
    def test_phrase_inside_sentence(self):
        self.assertTrue(is_wake_phrase("hello, hey rex, can you help"))
    def test_case_and_spacing(self):
        self.assertTrue(is_wake_phrase("HEY   REX"))
    def test_unrelated_phrase(self):
        self.assertFalse(is_wake_phrase("hey there"))
    def test_custom_phrase(self):
        self.assertTrue(is_wake_phrase("hello computer", "hello computer"))


if __name__ == "__main__":
    unittest.main()
