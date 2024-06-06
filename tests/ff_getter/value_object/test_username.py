import sys
import unittest

from ff_getter.value_object.user_name import UserName


class TestUserName(unittest.TestCase):
    def test_UserName(self):
        # 正常系
        name = "ユーザー名1"
        user_name = UserName(name)

        # 空白
        user_name = UserName("")

        # 異常系
        # 文字列でない
        with self.assertRaises(TypeError):
            user_name = UserName(-1)

    def test_name(self):
        name = "ユーザー名1"
        user_name = UserName(name)
        self.assertEqual(name, user_name.name)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
