import argparse
import datetime
import sys
import unittest
import warnings
from collections import namedtuple
from pathlib import Path

import orjson
from freezegun import freeze_time
from mock import MagicMock, patch

from ff_getter.core import Core, Result


class TestCore(unittest.TestCase):
    def setUp(self) -> None:
        warnings.simplefilter("ignore", ResourceWarning)

    def test_init(self):
        mock_logger = self.enterContext(patch("ff_getter.core.logger"))
        config = orjson.loads(Path("./config/config.json").read_bytes())

        core = Core()
        self.assertIsNone(core.parser)
        self.assertEqual(config, core.config)

        mock_parser = MagicMock(spec=argparse.ArgumentParser)
        reserved_file_num = 10
        mock_parser.parse_args.return_value.disable_notification = True
        mock_parser.parse_args.return_value.disable_after_open = True
        mock_parser.parse_args.return_value.reserved_file_num = reserved_file_num
        core = Core(mock_parser)
        self.assertFalse(core.config["notification"]["is_notify"])
        self.assertFalse(core.config["after_open"]["is_after_open"])
        self.assertTrue(core.config["move_old_file"]["is_move_old_file"])
        self.assertEqual(reserved_file_num, core.config["move_old_file"]["reserved_file_num"])

    def test_run(self):
        mock_twitter_follorwing = self.enterContext(patch("ff_getter.core.FollowingFetcher"))
        mock_twitter_follorwer = self.enterContext(patch("ff_getter.core.FollowerFetcher"))
        mock_directory = self.enterContext(patch("ff_getter.core.Directory"))
        mock_diff_following_list = self.enterContext(patch("ff_getter.core.DiffFollowingList"))
        mock_diff_follower_list = self.enterContext(patch("ff_getter.core.DiffFollowerList"))
        mock_notification = self.enterContext(patch("ff_getter.core.notification"))
        mock_subprocess = self.enterContext(patch("ff_getter.core.subprocess"))
        mock_logger = self.enterContext(patch("ff_getter.core.logger"))
        freeze_gun = self.enterContext(freeze_time("2023-03-20 00:00:00"))

        Params = namedtuple(
            "Params", ["is_notify", "is_move_old_file", "is_after_open", "is_moved_list", "is_error_occur"]
        )

        def pre_run(instance: Core, p: Params) -> Core:
            mock_twitter_follorwing.reset_mock()
            mock_twitter_follorwer.reset_mock()
            mock_directory.reset_mock()
            mock_diff_following_list.reset_mock()
            mock_diff_follower_list.reset_mock()
            mock_notification.reset_mock()
            mock_subprocess.reset_mock()

            following_fetcher = mock_twitter_follorwing.return_value
            following_fetcher.fetch.return_value = ["dummy_following_list"]
            follower_fetcher = mock_twitter_follorwer.return_value
            follower_fetcher.fetch.return_value = ["dummy_follower_list"]

            directory = mock_directory.return_value
            directory.get_last_following.return_value = ["dummy_prev_following_list"]
            directory.get_last_follower.return_value = ["dummy_prev_follower_list"]

            mock_diff_following_list.create_from_diff.return_value = ["dummy_diff_following_list"]
            mock_diff_follower_list.create_from_diff.return_value = ["dummy_diff_follower_list"]

            if p.is_error_occur:
                directory.save_file.side_effect = ValueError
            else:
                directory.save_file.return_value = "dummy_saved_file_path"
            directory.move_old_file.return_value = ["dummy_moved_old_file_path"] if p.is_moved_list else []

            instance.config["twitter_api_client"]["ct0"] = "dummy_ct0"
            instance.config["twitter_api_client"]["auth_token"] = "dummy_auth_token"
            instance.config["twitter_api_client"]["target_screen_name"] = "dummy_target_screen_name"
            instance.config["twitter_api_client"]["target_id"] = "dummy_target_id"
            instance.config["notification"]["is_notify"] = p.is_notify
            instance.config["after_open"]["is_after_open"] = p.is_after_open
            instance.config["move_old_file"]["is_move_old_file"] = p.is_move_old_file
            instance.config["move_old_file"]["reserved_file_num"] = 10 if p.is_move_old_file else -1
            return instance

        def post_run(instance: Core, p: Params) -> Core:
            mock_twitter_follorwing.assert_called_once_with(instance.config)
            mock_twitter_follorwer.assert_called_once_with(instance.config)

            following_fetcher = mock_twitter_follorwing.return_value
            following_fetcher.fetch.assert_called_once_with()
            follower_fetcher = mock_twitter_follorwer.return_value
            follower_fetcher.fetch.assert_called_once_with()

            directory = mock_directory.return_value
            directory.get_last_following.assert_called_once_with()
            directory.get_last_follower.assert_called_once_with()
            mock_diff_following_list.create_from_diff.assert_called_once_with(
                ["dummy_following_list"], ["dummy_prev_following_list"]
            )
            mock_diff_follower_list.create_from_diff.assert_called_once_with(
                ["dummy_follower_list"], ["dummy_prev_follower_list"]
            )
            target_screen_name = instance.config["twitter_api_client"]["target_screen_name"]
            directory.save_file.assert_called_once_with(
                target_screen_name,
                ["dummy_following_list"],
                ["dummy_follower_list"],
                ["dummy_diff_following_list"],
                ["dummy_diff_follower_list"],
            )

            if p.is_error_occur:
                mock_notification.notify.assert_not_called()
                directory.move_old_file.assert_not_called()
                mock_subprocess.Popen.assert_not_called()
                return instance

            is_notify = p.is_notify
            if is_notify:
                done_msg = "FFGetter run.\n"
                done_msg += datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                done_msg += " Process Done.\n"
                done_msg += f"follow num : {1} , "
                done_msg += f"follower num : {1}\n"
                mock_notification.notify.assert_called_once_with(
                    title="ffgetter",
                    message=done_msg,
                )
            else:
                mock_notification.notify.assert_not_called()

            is_move_old_file = p.is_move_old_file
            if is_move_old_file:
                reserved_file_num = 10
                directory.move_old_file.assert_called_once_with(reserved_file_num)
            else:
                directory.move_old_file.assert_not_called()

            is_after_open = p.is_after_open
            if is_after_open:
                mock_subprocess.Popen.assert_called_once_with(["start", "dummy_saved_file_path"], shell=True)
            else:
                mock_subprocess.Popen.assert_not_called()
            return instance

        params_list: tuple[list[Params], Result] = [
            (Params(True, True, True, True, False), Result.success),
            (Params(False, True, True, True, False), Result.success),
            (Params(True, False, True, True, False), Result.success),
            (Params(True, True, False, True, False), Result.success),
            (Params(True, True, True, False, False), Result.success),
            (Params(True, True, True, True, True), Result.failed),
        ]
        for params, expect in params_list:
            instance = Core()
            instance = pre_run(instance, params)
            actual = instance.run()
            self.assertEqual(expect, actual)
            post_run(instance, params)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
