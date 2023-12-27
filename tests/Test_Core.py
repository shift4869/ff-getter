# coding: utf-8
import argparse
import configparser
import datetime
import sys
import unittest
import warnings
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

from freezegun import freeze_time
from mock import MagicMock, patch

from ffgetter.Core import Core, FFGetResult
from ffgetter.TwitterAPI import TwitterAPI

logger = getLogger("ffgetter.Core")
logger.setLevel(WARNING)


class TestCore(unittest.TestCase):
    def setUp(self) -> None:
        warnings.simplefilter("ignore", ResourceWarning)

    def test_FFGetResult(self):
        expect = [
            "SUCCESS",
            "FAILED",
        ]
        actual = [item.name for item in FFGetResult]
        self.assertEqual(expect, actual)

    def test_Core(self):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))
            mock_logger_error = stack.enter_context(patch.object(logger, "error"))

            config = configparser.ConfigParser()
            config.read_file(Path("./config/config.ini").open("r", encoding="utf-8"))

            core = Core()
            self.assertIsNone(core.parser)
            self.assertEqual(config, core.config)

            mock_parser = MagicMock(spec=argparse.ArgumentParser)
            reserved_file_num = 10
            mock_parser.parse_args.return_value.disable_notification = True
            mock_parser.parse_args.return_value.disable_after_open = True
            mock_parser.parse_args.return_value.reserved_file_num = reserved_file_num
            core = Core(mock_parser)
            self.assertFalse(core.config["notification"].getboolean("is_notify"))
            self.assertFalse(core.config["after_open"].getboolean("is_after_open"))
            self.assertTrue(core.config["move_old_file"].getboolean("is_move_old_file"))
            self.assertEqual(str(reserved_file_num), core.config["move_old_file"]["reserved_file_num"])
            config.clear()

    def test_run(self):
        with ExitStack() as stack:
            mock_twitter_follorwing = stack.enter_context(patch("ffgetter.Core.NoAPIFollowingFetcher"))
            mock_twitter_follorwer = stack.enter_context(patch("ffgetter.Core.NoAPIFollowerFetcher"))
            mock_twitter = stack.enter_context(patch("ffgetter.Core.TwitterAPI"))
            mock_directory = stack.enter_context(patch("ffgetter.Core.Directory"))
            mock_diff_following_list = stack.enter_context(patch("ffgetter.Core.DiffFollowingList"))
            mock_diff_follower_list = stack.enter_context(patch("ffgetter.Core.DiffFollowerList"))
            mock_notification = stack.enter_context(patch("ffgetter.Core.notification"))
            mock_subprocess = stack.enter_context(patch("ffgetter.Core.subprocess"))
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))
            mock_logger_error = stack.enter_context(patch.object(logger, "error"))
            freeze_gun = stack.enter_context(freeze_time("2023-03-20 00:00:00"))

            following_fetcher = mock_twitter_follorwing.return_value
            following_fetcher.fetch.return_value = ["dummy_following_list"]
            follower_fetcher = mock_twitter_follorwer.return_value
            follower_fetcher.fetch.return_value = ["dummy_follower_list"]

            directory = mock_directory.return_value
            directory.get_last_following.return_value = ["dummy_prev_following_list"]
            directory.get_last_follower.return_value = ["dummy_prev_follower_list"]

            mock_diff_following_list.create_from_diff.return_value = ["dummy_diff_following_list"]
            mock_diff_follower_list.create_from_diff.return_value = ["dummy_diff_follower_list"]

            directory.save_file.return_value = "dummy_saved_file_path"
            directory.move_old_file.return_value = ["dummy_moved_old_file_path"]

            done_msg = "FFGetter run.\n"
            done_msg += datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            done_msg += " Process Done.\n"
            done_msg += f"follow num : {1} , "
            done_msg += f"follower num : {1}\n"

            core = Core()
            ct0 = core.config["twitter_api_client"]["ct0"]
            auth_token = core.config["twitter_api_client"]["auth_token"]
            target_screen_name = core.config["twitter_api_client"]["target_screen_name"]
            target_id = core.config["twitter_api_client"]["target_id"]

            # 分岐に関わらず実行されるメソッドの呼び出し確認用
            def check_common_mock_call():
                mock_twitter_follorwing.assert_called_once_with(ct0, auth_token, target_screen_name, target_id)
                mock_twitter_follorwer.assert_called_once_with(ct0, auth_token, target_screen_name, target_id)

                following_fetcher.fetch.assert_called_once_with()
                follower_fetcher.fetch.assert_called_once_with()

                directory.get_last_following.assert_called_once_with()
                directory.get_last_follower.assert_called_once_with()
                mock_diff_following_list.create_from_diff.assert_called_once_with(
                    ["dummy_following_list"],
                    ["dummy_prev_following_list"]
                )
                mock_diff_follower_list.create_from_diff.assert_called_once_with(
                    ["dummy_follower_list"],
                    ["dummy_prev_follower_list"]
                )
                directory.save_file.assert_called_once_with(
                    target_screen_name,
                    ["dummy_following_list"],
                    ["dummy_follower_list"],
                    ["dummy_diff_following_list"],
                    ["dummy_diff_follower_list"]
                )
                mock_twitter_follorwing.reset_mock()
                mock_twitter_follorwer.reset_mock()
                mock_directory.reset_mock()
                mock_diff_following_list.reset_mock()
                mock_diff_follower_list.reset_mock()

            # 正常系
            # すべての分岐でTrueとなるパターン
            core.config["notification"]["is_notify"] = "True"
            core.config["move_old_file"]["is_move_old_file"] = "True"
            core.config["move_old_file"]["reserved_file_num"] = "10"
            core.config["after_open"]["is_after_open"] = "True"
            actual = core.run()
            expect = FFGetResult.SUCCESS
            self.assertIs(expect, actual)
            mock_notification.notify.assert_called_once_with(
                title="ffgetter",
                message=done_msg,
            )
            mock_notification.reset_mock()
            reserved_file_num = int(core.config["move_old_file"]["reserved_file_num"])
            directory.move_old_file.assert_called_once_with(reserved_file_num)
            mock_subprocess.Popen.assert_called_once_with(["start", "dummy_saved_file_path"], shell=True)
            mock_subprocess.reset_mock()
            check_common_mock_call()

            # (7)完了後にファイルを開く のみFalse
            core.config["after_open"]["is_after_open"] = "False"
            actual = core.run()
            expect = FFGetResult.SUCCESS
            self.assertIs(expect, actual)
            mock_notification.notify.assert_called_once_with(
                title="ffgetter",
                message=done_msg,
            )
            mock_notification.reset_mock()
            reserved_file_num = int(core.config["move_old_file"]["reserved_file_num"])
            directory.move_old_file.assert_called_once_with(reserved_file_num)
            mock_subprocess.Popen.assert_not_called()
            mock_subprocess.reset_mock()
            check_common_mock_call()

            # (6)古いファイルを移動させる のみFalse
            core.config["move_old_file"]["is_move_old_file"] = "False"
            core.config["after_open"]["is_after_open"] = "True"
            actual = core.run()
            expect = FFGetResult.SUCCESS
            self.assertIs(expect, actual)
            mock_notification.notify.assert_called_once_with(
                title="ffgetter",
                message=done_msg,
            )
            mock_notification.reset_mock()
            reserved_file_num = int(core.config["move_old_file"]["reserved_file_num"])
            directory.move_old_file.assert_not_called()
            mock_subprocess.Popen.assert_called_once_with(["start", "dummy_saved_file_path"], shell=True)
            mock_subprocess.reset_mock()
            check_common_mock_call()

            # (5)完了通知 のみFalse
            core.config["notification"]["is_notify"] = "False"
            core.config["move_old_file"]["is_move_old_file"] = "True"
            actual = core.run()
            expect = FFGetResult.SUCCESS
            self.assertIs(expect, actual)
            mock_notification.notify.assert_not_called()
            reserved_file_num = int(core.config["move_old_file"]["reserved_file_num"])
            directory.move_old_file.assert_called_once_with(reserved_file_num)
            mock_subprocess.Popen.assert_called_once_with(["start", "dummy_saved_file_path"], shell=True)
            mock_subprocess.reset_mock()
            check_common_mock_call()

            # 異常系
            mock_twitter_follorwing.side_effect = ValueError
            actual = core.run()
            expect = FFGetResult.FAILED
            self.assertIs(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
