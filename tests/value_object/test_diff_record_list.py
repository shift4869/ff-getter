import sys
import unittest

from ffgetter.value_object.diff_record import DiffRecord
from ffgetter.value_object.diff_record_list import DiffFollowerList, DiffFollowingList, DiffRecordList
from ffgetter.value_object.user_record import UserRecord
from ffgetter.value_object.user_record_list import UserRecordList


class TestDiffRecordList(unittest.TestCase):
    def test_DiffRecordList(self):
        diff_record = DiffRecord.create("ADD", 1, "ユーザー1", "screen_name_1")
        diff_record_list = DiffRecordList([diff_record])
        self.assertEqual([diff_record], diff_record_list._list)

        diff_record_list = DiffRecordList([])
        self.assertEqual([], diff_record_list._list)

        diff_record_list = DiffRecordList([diff_record, diff_record])
        for r in diff_record_list:
            self.assertEqual(diff_record, r)
        self.assertEqual(2, len(diff_record_list))

        with self.assertRaises(TypeError):
            diff_record = DiffRecordList(["invalid_arg"])
        with self.assertRaises(TypeError):
            diff_record = DiffRecordList("invalid_arg")

    def test_create(self):
        diff_record = DiffRecord.create("ADD", 1, "ユーザー1", "screen_name_1")

        actual = DiffRecordList.create([diff_record])
        expect = DiffRecordList([diff_record])
        self.assertEqual(expect, actual)

        actual = DiffRecordList.create(diff_record)
        expect = DiffRecordList([diff_record])
        self.assertEqual(expect, actual)

        actual = DiffRecordList.create([])
        expect = DiffRecordList([])
        self.assertEqual(expect, actual)

        actual = DiffRecordList.create()
        expect = DiffRecordList([])
        self.assertEqual(expect, actual)

    def test_create_from_diff(self):
        user_record_1 = UserRecord.create(1, "ユーザー1", "screen_name_1")
        user_record_2 = UserRecord.create(2, "ユーザー2", "screen_name_2")
        user_record_3 = UserRecord.create(3, "ユーザー3", "screen_name_3")
        user_record_list_1 = UserRecordList.create([user_record_1, user_record_2])
        user_record_list_2 = UserRecordList.create([user_record_2, user_record_3])
        actual = DiffRecordList.create_from_diff(user_record_list_1, user_record_list_2)

        diff_record_1 = DiffRecord.create("ADD", 1, "ユーザー1", "screen_name_1")
        diff_record_3 = DiffRecord.create("REMOVE", 3, "ユーザー3", "screen_name_3")
        expect = DiffRecordList.create([diff_record_1, diff_record_3])
        self.assertEqual(expect, actual)

        actual = DiffRecordList.create_from_diff(user_record_list_1, [])
        expect = DiffRecordList.create()
        self.assertEqual(expect, actual)

    def test_ff(self):
        diff_record = DiffRecord.create("ADD", 1, "ユーザー1", "screen_name_1")

        actual = DiffFollowingList.create([diff_record])
        self.assertIsInstance(actual, DiffRecordList)
        self.assertIsInstance(actual, DiffFollowingList)
        self.assertNotIsInstance(actual, DiffFollowerList)

        actual = DiffFollowerList.create([diff_record])
        self.assertIsInstance(actual, DiffRecordList)
        self.assertNotIsInstance(actual, DiffFollowingList)
        self.assertIsInstance(actual, DiffFollowerList)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
