import sys
import unittest

from ffgetter.value_object.diff_record import DiffFollower, DiffFollowing, DiffRecord, DiffType
from ffgetter.value_object.screen_name import ScreenName
from ffgetter.value_object.user_id import UserId
from ffgetter.value_object.user_name import UserName


class TestDiffRecord(unittest.TestCase):
    def test_diff_type(self):
        expect = [
            ("ADD", "ADD"),
            ("REMOVE", "REMOVE"),
        ]
        actual = [(item.name, item.value) for item in DiffType]
        self.assertEqual(expect, actual)

    def test_DiffRecord(self):
        diff_type = DiffType.ADD
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")
        diff_record = DiffRecord(diff_type, user_id, user_name, screen_name)

        self.assertEqual(DiffType.ADD, diff_record.diff_type)
        self.assertEqual(user_id, diff_record.id)
        self.assertEqual(user_name, diff_record.name)
        self.assertEqual(screen_name, diff_record.screen_name)

        with self.assertRaises(TypeError):
            diff_record = DiffRecord("invalid_arg", user_id, user_name, screen_name)
        with self.assertRaises(TypeError):
            diff_record = DiffRecord(diff_type, "invalid_arg", user_name, screen_name)
        with self.assertRaises(TypeError):
            diff_record = DiffRecord(diff_type, user_id, "invalid_arg", screen_name)
        with self.assertRaises(TypeError):
            diff_record = DiffRecord(diff_type, user_id, user_name, "invalid_arg")

    def test_line(self):
        diff_type = DiffType.ADD
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")
        user_record = DiffRecord(diff_type, user_id, user_name, screen_name)
        expect = "{}, {}, {}, {}".format(
            diff_type.value,
            user_id.id_str,
            user_name.name,
            screen_name.name,
        )
        self.assertEqual(expect, user_record.line)

    def test_create(self):
        diff_type = DiffType.ADD
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")
        actual = DiffRecord.create(diff_type.value, user_id.id, user_name.name, screen_name.name)
        expect = DiffRecord(diff_type, user_id, user_name, screen_name)
        self.assertEqual(expect, actual)

        diff_type = DiffType.REMOVE
        actual = DiffRecord.create(diff_type.value, user_id.id, user_name.name, screen_name.name)
        expect = DiffRecord(diff_type, user_id, user_name, screen_name)
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = DiffRecord.create("invalid_diff_type", user_id.id, user_name.name, screen_name.name)

    def test_ff(self):
        diff_type = DiffType.ADD
        user_id = UserId(123)
        user_name = UserName("ユーザー1")
        screen_name = ScreenName("screen_name_1")

        actual = DiffFollowing.create(diff_type.value, user_id.id, user_name.name, screen_name.name)
        self.assertIsInstance(actual, DiffRecord)
        self.assertIsInstance(actual, DiffFollowing)
        self.assertNotIsInstance(actual, DiffFollower)

        actual = DiffFollower.create(diff_type.value, user_id.id, user_name.name, screen_name.name)
        self.assertIsInstance(actual, DiffRecord)
        self.assertNotIsInstance(actual, DiffFollowing)
        self.assertIsInstance(actual, DiffFollower)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
