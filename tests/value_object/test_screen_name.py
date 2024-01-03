import sys
import unittest

from ffgetter.value_object.screen_name import ScreenName


class TestScreenName(unittest.TestCase):
    def test_ScreenName(self):
        name = "screen_name_1"
        screen_name = ScreenName(name)

        PATTERN = "^[0-9a-zA-Z_]+$"
        self.assertEqual(PATTERN, ScreenName.PATTERN)

        with self.assertRaises(TypeError):
            screen_name = ScreenName(-1)
        with self.assertRaises(ValueError):
            screen_name = ScreenName("不正なスクリーンネーム")
        with self.assertRaises(ValueError):
            screen_name = ScreenName("")

    def test_name(self):
        name = "screen_name_1"
        screen_name = ScreenName(name)
        self.assertEqual(name, screen_name.name)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
