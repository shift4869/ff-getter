# coding: utf-8
import sys
import unittest

from ffgetter.value_object.ScreenName import ScreenName
from ffgetter.value_object.UserId import UserId
from ffgetter.value_object.UserName import UserName
from ffgetter.value_object.UserRecord import Follower, Following, UserRecord


class TestUserRecord(unittest.TestCase):
    def test_UserRecord(self):
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")
        user_record = UserRecord(user_id, user_name, screen_name)

        self.assertEqual(user_id, user_record.id)
        self.assertEqual(user_name, user_record.name)
        self.assertEqual(screen_name, user_record.screen_name)

        with self.assertRaises(TypeError):
            user_record = UserRecord("invalid_arg", user_name, screen_name)
        with self.assertRaises(TypeError):
            user_record = UserRecord(user_id, "invalid_arg", screen_name)
        with self.assertRaises(TypeError):
            user_record = UserRecord(user_id, user_name, "invalid_arg")

    def test_line(self):
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")
        user_record = UserRecord(user_id, user_name, screen_name)
        expect = "{}, {}, {}".format(
            user_id.id_str,
            user_name.name,
            screen_name.name,
        )
        self.assertEqual(expect, user_record.line)

    def test_to_dict(self):
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")
        user_record = UserRecord(user_id, user_name, screen_name)
        expect = {
            "id": user_id.id_str,
            "name": user_name.name,
            "screen_name": screen_name.name,
        }
        self.assertEqual(expect, user_record.to_dict())

    def test_create(self):
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")
        actual = UserRecord.create(user_id.id, user_name.name, screen_name.name)
        expect = UserRecord(user_id, user_name, screen_name)
        self.assertEqual(expect, actual)

    def test_ff(self):
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")

        actual = Following(user_id, user_name, screen_name)
        self.assertIsInstance(actual, UserRecord)
        self.assertIsInstance(actual, Following)
        self.assertNotIsInstance(actual, Follower)

        actual = Following.create(user_id.id, user_name.name, screen_name.name)
        self.assertIsInstance(actual, UserRecord)
        self.assertIsInstance(actual, Following)
        self.assertNotIsInstance(actual, Follower)

        actual = Follower(user_id, user_name, screen_name)
        self.assertIsInstance(actual, UserRecord)
        self.assertNotIsInstance(actual, Following)
        self.assertIsInstance(actual, Follower)

        actual = Follower.create(user_id.id, user_name.name, screen_name.name)
        self.assertIsInstance(actual, UserRecord)
        self.assertNotIsInstance(actual, Following)
        self.assertIsInstance(actual, Follower)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
