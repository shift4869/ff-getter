# coding: utf-8
import sys
import unittest

from ffgetter.value_object.UserRecord import UserRecord
from ffgetter.value_object.UserRecordList import FollowerList, FollowingList, UserRecordList


class TestUserRecordList(unittest.TestCase):
    def test_UserRecordList(self):
        user_record = UserRecord.create(123, "ユーザー1", "screen_name_1")
        user_record_list = UserRecordList([user_record])
        self.assertEqual([user_record], user_record_list._list)

        user_record_list = UserRecordList([])
        self.assertEqual([], user_record_list._list)

        user_record_list = UserRecordList([user_record, user_record])
        for r in user_record_list:
            self.assertEqual(user_record, r)
        self.assertEqual(2, len(user_record_list))

        with self.assertRaises(TypeError):
            user_record = UserRecordList(["invalid_arg"])
        with self.assertRaises(TypeError):
            user_record = UserRecordList("invalid_arg")

    def test_create(self):
        user_record = UserRecord.create(123, "ユーザー1", "screen_name_1")

        actual = UserRecordList.create([user_record])
        expect = UserRecordList([user_record])
        self.assertEqual(expect, actual)

        actual = UserRecordList.create(user_record)
        expect = UserRecordList([user_record])
        self.assertEqual(expect, actual)

        actual = UserRecordList.create([])
        expect = UserRecordList([])
        self.assertEqual(expect, actual)

        actual = UserRecordList.create()
        expect = UserRecordList([])
        self.assertEqual(expect, actual)

    def test_ff(self):
        user_record = UserRecord.create(123, "ユーザー1", "screen_name_1")

        actual = FollowingList.create([user_record])
        self.assertIsInstance(actual, UserRecordList)
        self.assertIsInstance(actual, FollowingList)
        self.assertNotIsInstance(actual, FollowerList)

        actual = FollowerList.create([user_record])
        self.assertIsInstance(actual, UserRecordList)
        self.assertNotIsInstance(actual, FollowingList)
        self.assertIsInstance(actual, FollowerList)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
