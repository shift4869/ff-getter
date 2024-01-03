import datetime
import os
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
    def _get_instance(self):
        # カレントディレクトリを tests に移動させる
        directory = Directory()
        base_path = Path(os.path.dirname(__file__)).parent / "tests"
        object.__setattr__(directory, "base_path", base_path)
        directory.set_current()
        return directory

    def _make_sample_file(self) -> Path:
        directory = Directory()
        template_str = ""
        template_file_path = Path(os.path.dirname(__file__)).parent / directory.TEMPLATE_FILE_PATH
        with template_file_path.open("r") as fin:
            template_str = fin.read()

        template: Template = Template(template_str)
        yesterday_str = "20230317"
        test_base_path = Path(os.path.dirname(__file__)).parent / "tests"
        file_path = test_base_path / directory.RESULT_DIRECTORY / f"{directory.FILE_NAME_BASE}_{yesterday_str}.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)

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
        difference_caption = f"difference with nothing (first run)"

        rendered_str = template.render(
            {
                "today_str": yesterday_str,
                "target_username": target_username,
                "following_caption": following_caption,
                "following_list": t_following_list,
                "follower_caption": follower_caption,
                "follower_list": t_follower_list,
                "difference_caption": difference_caption,
                "diff_following_list": t_diff_following_list,
                "diff_follower_list": t_diff_follower_list,
            }
        )
        with file_path.open("w", encoding="utf-8") as fout:
            fout.write(rendered_str)
        return file_path

    def test_Directory(self):
        directory = Directory()
        expect = Path(os.path.dirname(__file__)).parent
        self.assertEqual(expect, directory.base_path)

        FILE_NAME_BASE = "ff_list"
        RESULT_DIRECTORY = "./result/"
        BACKUP_DIRECTORY = "./bak/"
        TEMPLATE_FILE_PATH = "./ext/template.txt"
        self.assertEqual(FILE_NAME_BASE, Directory.FILE_NAME_BASE)
        self.assertEqual(RESULT_DIRECTORY, Directory.RESULT_DIRECTORY)
        self.assertEqual(BACKUP_DIRECTORY, Directory.BACKUP_DIRECTORY)
        self.assertEqual(TEMPLATE_FILE_PATH, Directory.TEMPLATE_FILE_PATH)

    def test_set_current(self):
        directory = Directory()
        expect = Path(os.path.dirname(__file__)).parent
        self.assertEqual(expect, directory.set_current())

    def test_get_last_file_path(self):
        with freeze_time("2023-03-18 00:00:00"):
            directory = self._get_instance()
            result_directory_path = Path(directory.RESULT_DIRECTORY)
            if result_directory_path.is_dir():
                shutil.rmtree(result_directory_path)
            result_directory_path.mkdir(parents=True, exist_ok=True)

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

            # 後始末
            if result_directory_path.is_dir():
                shutil.rmtree(result_directory_path)

    def test_get_last_following(self):
        self._make_sample_file()
        directory = self._get_instance()
        actual = directory.get_last_following()

        user_record_1 = Following.create(1, "ユーザー1", "screen_name_1")
        user_record_2 = Following.create(2, "ユーザー2", "screen_name_2")
        expect = FollowingList.create([user_record_1, user_record_2])
        self.assertEqual(expect, actual)

        # 後始末
        result_directory_path = Path(directory.RESULT_DIRECTORY)
        if result_directory_path.is_dir():
            shutil.rmtree(result_directory_path)

    def test_get_last_follower(self):
        self._make_sample_file()
        directory = self._get_instance()
        actual = directory.get_last_follower()

        user_record_2 = Follower.create(2, "ユーザー2", "screen_name_2")
        user_record_3 = Follower.create(3, "ユーザー3", "screen_name_3")
        expect = FollowerList.create([user_record_2, user_record_3])
        self.assertEqual(expect, actual)

        # 後始末
        result_directory_path = Path(directory.RESULT_DIRECTORY)
        if result_directory_path.is_dir():
            shutil.rmtree(result_directory_path)

    def test_save_file(self):
        with freeze_time("2023-03-18 00:00:00"):
            directory = Directory()
            object.__setattr__(directory, "RESULT_DIRECTORY", "./tests/result")
            Path(directory.RESULT_DIRECTORY).mkdir(parents=True, exist_ok=True)

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
            actual = directory.save_file(target_username, following_list, follower_list, diff_following_list, diff_follower_list)
            expect = self._make_sample_file()
            expect_str = str(expect.absolute()).replace(yesterday_str, today_str)  # 日付部分の差異は吸収
            self.assertEqual(expect_str, str(actual.absolute()))

            file_path = Path(directory.RESULT_DIRECTORY) / f"{directory.FILE_NAME_BASE}_{today_str}.txt"
            with file_path.open("r") as fin:
                actual = fin.read()

            file_path = Path(directory.RESULT_DIRECTORY) / f"{directory.FILE_NAME_BASE}_{yesterday_str}.txt"
            with file_path.open("r") as fin:
                expect = fin.read()
            expect = expect.replace(yesterday_str, today_str)  # 日付部分の差異は吸収
            self.assertEqual(expect, actual)

            # 後始末
            result_directory_path = Path(directory.RESULT_DIRECTORY)
            if result_directory_path.is_dir():
                shutil.rmtree(result_directory_path)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
