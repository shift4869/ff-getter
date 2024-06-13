import shutil
import sys
import unittest
from pathlib import Path

from freezegun import freeze_time
from jinja2 import Template

from ff_getter.directory import Directory
from ff_getter.value_object.diff_record import DiffFollower, DiffFollowing, DiffRecord
from ff_getter.value_object.diff_record_list import DiffFollowerList, DiffFollowingList, DiffRecordList
from ff_getter.value_object.user_record import Follower, Following, UserRecord
from ff_getter.value_object.user_record_list import FollowerList, FollowingList, UserRecordList


class TestDirectory(unittest.TestCase):
    def setUp(self) -> None:
        temp_directory_path_list = [
            Path("./tests/ff_getter/result"),
            Path("./tests/ff_getter/bak"),
        ]
        for temp_directory_path in temp_directory_path_list:
            self._init_path(temp_directory_path)
        return super().setUp()

    def tearDown(self) -> None:
        temp_directory_path_list = [
            Path("./tests/ff_getter/result"),
            Path("./tests/ff_getter/bak"),
        ]
        for temp_directory_path in temp_directory_path_list:
            self._del_path(temp_directory_path)
        return super().tearDown()

    def _del_path(self, directory_path: Path) -> None:
        directory_path.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(directory_path)

    def _init_path(self, directory_path: Path) -> None:
        self._del_path(directory_path)
        directory_path.mkdir(parents=True, exist_ok=True)

    def _get_instance(self):
        directory = Directory()
        base_path = Path("./tests/ff_getter")
        object.__setattr__(directory, "base_path", base_path)
        object.__setattr__(directory, "RESULT_DIRECTORY", "./tests/ff_getter/result")
        object.__setattr__(directory, "BACKUP_DIRECTORY", "./tests/ff_getter/bak")
        return directory

    def _make_sample_file(self, date_str) -> Path:
        directory = self._get_instance()
        template_str = ""
        template_file_path = Path(directory.TEMPLATE_FILE_PATH)
        template_str = template_file_path.read_text(encoding="utf8")

        template: Template = Template(template_str)
        file_path: Path = Path(directory.RESULT_DIRECTORY) / f"{directory.FILE_NAME_BASE}_{date_str}.txt"

        last_file_path = directory.get_last_file_path()

        target_username = "dummy_target_username"
        user_record_1 = UserRecord.create(1, "ユーザー1", "screen_name_1")
        user_record_2 = UserRecord.create(2, "ユーザー2", "screen_name_2")
        user_record_3 = UserRecord.create(3, "ユーザー3", "screen_name_3")
        user_record_list_1 = UserRecordList.create([user_record_1, user_record_2])
        user_record_list_2 = UserRecordList.create([user_record_2, user_record_3])

        diff_record_1 = DiffRecord.create("ADD", 1, "ユーザー1", "screen_name_1")
        diff_record_3 = DiffRecord.create("REMOVE", 3, "ユーザー3", "screen_name_3")
        diff_record_list_1 = DiffRecordList.create([diff_record_1])
        diff_record_list_2 = DiffRecordList.create([diff_record_3])

        t_following_list = [r.line + "\n" for r in user_record_list_1]
        t_follower_list = [r.line + "\n" for r in user_record_list_2]
        t_diff_following_list = [r.line + "\n" for r in diff_record_list_1]
        t_diff_follower_list = [r.line + "\n" for r in diff_record_list_2]

        following_num = len(t_following_list)
        follower_num = len(t_follower_list)
        following_caption = f"following {following_num}"
        follower_caption = f"follower {follower_num}"
        difference_caption = ""
        if last_file_path:
            difference_caption = f"difference with {last_file_path.name}"
        else:
            difference_caption = f"difference with nothing (first run)"

        rendered_str = template.render({
            "today_str": date_str,
            "target_username": target_username,
            "following_caption": following_caption,
            "following_list": t_following_list,
            "follower_caption": follower_caption,
            "follower_list": t_follower_list,
            "difference_caption": difference_caption,
            "diff_following_list": t_diff_following_list,
            "diff_follower_list": t_diff_follower_list,
        })
        file_path.write_text(rendered_str, encoding="utf8")
        return file_path

    def test_init(self):
        directory = Directory()
        expect = Path().resolve()
        self.assertEqual(expect, directory.base_path)

        FILE_NAME_BASE = "ff_list"
        RESULT_DIRECTORY = "./result/"
        BACKUP_DIRECTORY = "./bak/"
        TEMPLATE_FILE_PATH = "./ext/template.txt"
        self.assertEqual(FILE_NAME_BASE, Directory.FILE_NAME_BASE)
        self.assertEqual(RESULT_DIRECTORY, Directory.RESULT_DIRECTORY)
        self.assertEqual(BACKUP_DIRECTORY, Directory.BACKUP_DIRECTORY)
        self.assertEqual(TEMPLATE_FILE_PATH, Directory.TEMPLATE_FILE_PATH)

    def test_get_last_file_path(self):
        self.enterContext(freeze_time("2023-03-18 00:00:00"))
        directory = self._get_instance()
        result_directory_path = Path(directory.RESULT_DIRECTORY)

        # 前回実行ファイルが無かった = 初回実行
        actual = directory.get_last_file_path()
        self.assertIsNone(actual)

        # 前回実行のうち最新のパスを保持
        today_str = "20230317"
        file_path = result_directory_path / f"{directory.FILE_NAME_BASE}_{today_str}.txt"
        file_path.touch()
        actual = directory.get_last_file_path()
        expect = file_path
        self.assertEqual(expect, actual)

        # 今日と同じ日付がファイル名に含まれる = 初回実行ではないが実行済
        today_str = "20230318"
        yesterday_str = "20230317"
        file_path = result_directory_path / f"{directory.FILE_NAME_BASE}_{today_str}.txt"
        file_path.touch()
        actual = directory.get_last_file_path()
        expect = result_directory_path / f"{directory.FILE_NAME_BASE}_{yesterday_str}.txt"
        self.assertEqual(expect, actual)
        expect.unlink(missing_ok=True)

        # 本日実行分しかなかったため、前回実行分は無かった
        actual = directory.get_last_file_path()
        self.assertIsNone(actual)

    def test_get_last_following(self):
        directory = self._get_instance()
        # result が空の場合
        actual = directory.get_last_following()
        expect = FollowingList.create()
        self.assertEqual(expect, actual)

        # result に前回実行ファイルが存在する場合
        self._make_sample_file("20230317")
        actual = directory.get_last_following()
        user_record_1 = Following.create(1, "ユーザー1", "screen_name_1")
        user_record_2 = Following.create(2, "ユーザー2", "screen_name_2")
        expect = FollowingList.create([user_record_1, user_record_2])
        self.assertEqual(expect, actual)

    def test_get_last_follower(self):
        directory = self._get_instance()
        # result が空の場合
        actual = directory.get_last_follower()
        expect = FollowerList.create()
        self.assertEqual(expect, actual)

        # result に前回実行ファイルが存在する場合
        self._make_sample_file("20230317")
        actual = directory.get_last_follower()
        user_record_2 = Follower.create(2, "ユーザー2", "screen_name_2")
        user_record_3 = Follower.create(3, "ユーザー3", "screen_name_3")
        expect = FollowerList.create([user_record_2, user_record_3])
        self.assertEqual(expect, actual)

    def test_save_file(self):
        self.enterContext(freeze_time("2023-03-18 00:00:00"))
        directory = self._get_instance()

        target_username = "dummy_target_username"
        following_1 = Following.create(1, "ユーザー1", "screen_name_1")
        following_2 = Following.create(2, "ユーザー2", "screen_name_2")
        follower_2 = Follower.create(2, "ユーザー2", "screen_name_2")
        follower_3 = Follower.create(3, "ユーザー3", "screen_name_3")
        following_list = FollowingList.create([following_1, following_2])
        follower_list = FollowerList.create([follower_2, follower_3])

        diff_following_1 = DiffFollowing.create("ADD", 1, "ユーザー1", "screen_name_1")
        diff_follower_3 = DiffFollower.create("REMOVE", 3, "ユーザー3", "screen_name_3")
        diff_following_list = DiffFollowingList.create([diff_following_1])
        diff_follower_list = DiffFollowerList.create([diff_follower_3])

        today_str = "20230318"
        yesterday_str = "20230317"

        # result が空の場合
        expect: Path = self._make_sample_file(today_str)
        expect_str: str = expect.read_text(encoding="utf8")
        expect.unlink(missing_ok=True)

        actual: Path = directory.save_file(
            target_username, following_list, follower_list, diff_following_list, diff_follower_list
        )
        self.assertEqual(str(expect.absolute()), str(actual.absolute()))

        file_path: Path = Path(directory.RESULT_DIRECTORY) / f"{directory.FILE_NAME_BASE}_{today_str}.txt"
        actual_str: str = file_path.read_text(encoding="utf8")
        self.assertEqual(expect_str, actual_str)

        # result に前回実行ファイルが存在する場合
        self._make_sample_file(yesterday_str)
        expect: Path = self._make_sample_file(today_str)
        expect_str: str = expect.read_text(encoding="utf8")
        expect.unlink(missing_ok=True)

        actual: Path = directory.save_file(
            target_username, following_list, follower_list, diff_following_list, diff_follower_list
        )
        self.assertEqual(str(expect.absolute()), str(actual.absolute()))

        file_path: Path = Path(directory.RESULT_DIRECTORY) / f"{directory.FILE_NAME_BASE}_{today_str}.txt"
        actual_str: str = file_path.read_text(encoding="utf8")
        self.assertEqual(expect_str, actual_str)

    def test_move_old_file(self):
        self.enterContext(freeze_time("2023-03-18 00:00:00"))
        directory = self._get_instance()

        reserved_file_num = 10
        result_path = Path(directory.RESULT_DIRECTORY)
        backup_path = Path(directory.BACKUP_DIRECTORY)
        file_name_base = directory.FILE_NAME_BASE

        # reserved_file_num が不正
        actual = directory.move_old_file("invalid_str")
        self.assertEqual([], actual)
        actual = directory.move_old_file(-1)
        self.assertEqual([], actual)

        # RESULT_DIRECTORY にあるファイル数が reserved_file_num 以下
        self._init_path(result_path)
        self._init_path(backup_path)
        for index in range(reserved_file_num // 2):
            (result_path / f"{file_name_base}_{index}.txt").touch()
        actual = directory.move_old_file(reserved_file_num)
        self.assertEqual([], actual)

        self._init_path(result_path)
        self._init_path(backup_path)
        for index in range(reserved_file_num):
            (result_path / f"{file_name_base}_{index}.txt").touch()
        actual = directory.move_old_file(reserved_file_num)
        self.assertEqual([], actual)

        # RESULT_DIRECTORY にあるファイル数を BACKUP_DIRECTORY に移動
        over_num = 5
        self._init_path(result_path)
        self._init_path(backup_path)
        for index in range(reserved_file_num + over_num):
            (result_path / f"{file_name_base}_{index}.txt").touch()
        actual = directory.move_old_file(reserved_file_num)
        expect = list(backup_path.glob(f"{file_name_base}*"))
        self.assertEqual(expect, actual)
        reserved_file = list(result_path.glob(f"{file_name_base}*"))
        self.assertEqual(reserved_file_num, len(reserved_file))

        # 移動先に同じファイル名のファイルが存在していた
        over_num = 5
        self._init_path(result_path)
        self._init_path(backup_path)
        for index in range(reserved_file_num + over_num):
            (result_path / f"{file_name_base}_{index}.txt").touch()
        for index in range(over_num):
            (backup_path / f"{file_name_base}_{index}.txt").touch()
        with self.assertRaises(FileExistsError):
            actual = directory.move_old_file(reserved_file_num)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
