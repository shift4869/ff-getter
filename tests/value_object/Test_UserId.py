# coding: utf-8
import sys
import unittest

from ffgetter.value_object.UserId import UserId


class TestUserId(unittest.TestCase):
    def test_UserId(self):
        id_num = 12345678
        user_id = UserId(id_num)
        user_id = UserId(0)

        with self.assertRaises(TypeError):
            user_id = UserId("12345678")
        with self.assertRaises(ValueError):
            user_id = UserId(-1)

    def test_id_num(self):
        id_num = 12345678
        user_id = UserId(id_num)
        self.assertTrue(isinstance(user_id.id, int))
        self.assertEqual(id_num, user_id.id)
        self.assertTrue(isinstance(user_id.id_str, str))
        self.assertEqual(str(id_num), user_id.id_str)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
