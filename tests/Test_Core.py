# coding: utf-8
import configparser
import datetime
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

from freezegun import freeze_time
from mock import MagicMock, call, patch

from ffgetter.Core import Core, FFGetResult
from ffgetter.TwitterAPI import TwitterAPI
from ffgetter.value_object.DiffRecordList import DiffFollowerList, DiffFollowingList

logger = getLogger("ffgetter.Core")
logger.setLevel(WARNING)


class TestCore(unittest.TestCase):
    def test_FFGetResult(self):
        expect = [
            "SUCCESS",
            "FAILED",
        ]
        actual = [item.name for item in FFGetResult]
        self.assertEqual(expect, actual)

    def test_Core(self):
        with ExitStack() as stack:
            mock_twitter = stack.enter_context(patch("ffgetter.Core.TwitterAPI"))
            mock_twitter.return_value = MagicMock(spec=TwitterAPI)

            config = configparser.ConfigParser()
            config.read_file(Path("./config/config.ini").open("r", encoding="utf-8"))

            config_twitter_token = config["twitter_token_keys_v2"]
            API_KEY = config_twitter_token["api_key"]
            API_KEY_SECRET = config_twitter_token["api_key_secret"]
            ACCESS_TOKEN_KEY = config_twitter_token["access_token"]
            ACCESS_TOKEN_SECRET = config_twitter_token["access_token_secret"]

            core = Core()
            self.assertEqual(config, core.config)
            self.assertIsInstance(core.twitter_api, TwitterAPI)
            mock_twitter.assert_called_once_with(
                API_KEY,
                API_KEY_SECRET,
                ACCESS_TOKEN_KEY,
                ACCESS_TOKEN_SECRET
            )

    def test_run(self):
        with ExitStack() as stack:
            mock_twitter = stack.enter_context(patch("ffgetter.Core.TwitterAPI"))
            mock_directory = stack.enter_context(patch("ffgetter.Core.Directory"))
            mock_diff_following_list = stack.enter_context(patch("ffgetter.Core.DiffFollowingList"))
            mock_diff_follower_list = stack.enter_context(patch("ffgetter.Core.DiffFollowerList"))
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))
            mock_logger_error = stack.enter_context(patch.object(logger, "error"))
            freeze_gun = stack.enter_context(freeze_time("2023-03-20 00:00:00"))

            twitter_api = mock_twitter.return_value
            twitter_api.get_user_id.return_value = "dummy_user_id"
            twitter_api.get_following.return_value = ["dummy_following_list"]
            twitter_api.get_follower.return_value = ["dummy_follower_list"]

            directory = mock_directory.return_value
            directory.get_last_following.return_value = ["dummy_prev_following_list"]
            directory.get_last_follower.return_value = ["dummy_prev_follower_list"]

            mock_diff_following_list.create_from_diff.return_value = ["dummy_diff_following_list"]
            mock_diff_follower_list.create_from_diff.return_value = ["dummy_diff_follower_list"]

            directory.save_file.return_value = "dummy_saved_text"

            done_msg = "FFGetter run.\n"
            done_msg += datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            done_msg += " Process Done.\n"
            done_msg += f"follow num : {1} , "
            done_msg += f"follower num : {1}\n"

            core = Core()
            core.config["notification"]["reply_to_user_name"] = ""
            actual = core.run()
            expect = FFGetResult.SUCCESS
            self.assertIs(expect, actual)

            twitter_api.get_user_id.assert_called_once_with()
            twitter_api.get_following.assert_called_once_with("dummy_user_id")
            twitter_api.get_follower.assert_called_once_with("dummy_user_id")
            directory.get_last_following.assert_called_once_with()
            directory.get_last_follower.assert_called_once_with()
            mock_diff_following_list.create_from_diff.assert_called_once_with(["dummy_following_list"], ["dummy_prev_following_list"])
            mock_diff_follower_list.create_from_diff.assert_called_once_with(["dummy_follower_list"], ["dummy_prev_follower_list"])
            directory.save_file.assert_called_once_with(
                ["dummy_following_list"], ["dummy_follower_list"], ["dummy_diff_following_list"], ["dummy_diff_follower_list"]
            )
            twitter_api.post_tweet.assert_not_called()

            mock_twitter.reset_mock()
            mock_directory.reset_mock()
            mock_diff_following_list.reset_mock()
            mock_diff_follower_list.reset_mock()

            core.config["notification"]["reply_to_user_name"] = "dummy_user_name"
            tweet_str = "@" + "dummy_user_name" + " " + done_msg
            actual = core.run()
            expect = FFGetResult.SUCCESS
            self.assertIs(expect, actual)

            twitter_api.get_user_id.assert_called_once_with()
            twitter_api.get_following.assert_called_once_with("dummy_user_id")
            twitter_api.get_follower.assert_called_once_with("dummy_user_id")
            directory.get_last_following.assert_called_once_with()
            directory.get_last_follower.assert_called_once_with()
            mock_diff_following_list.create_from_diff.assert_called_once_with(["dummy_following_list"], ["dummy_prev_following_list"])
            mock_diff_follower_list.create_from_diff.assert_called_once_with(["dummy_follower_list"], ["dummy_prev_follower_list"])
            directory.save_file.assert_called_once_with(
                ["dummy_following_list"], ["dummy_follower_list"], ["dummy_diff_following_list"], ["dummy_diff_follower_list"]
            )
            twitter_api.post_tweet.assert_called_once_with(tweet_str)

            twitter_api.get_user_id.side_effect = ValueError
            actual = core.run()
            expect = FFGetResult.FAILED
            self.assertIs(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
