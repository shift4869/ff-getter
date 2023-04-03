# coding: utf-8
import argparse
import configparser
import datetime
import os
import subprocess
from dataclasses import dataclass
from enum import Enum, auto
from logging import INFO, getLogger
from pathlib import Path
from typing import ClassVar

from ffgetter.Directory import Directory
from ffgetter.noapi.NoAPIFFFetcherBase import NoAPIFollowerFetcher, NoAPIFollowingFetcher
from ffgetter.TwitterAPI import TwitterAPI
from ffgetter.value_object.DiffRecordList import DiffFollowerList, DiffFollowingList
from ffgetter.value_object.ScreenName import ScreenName

logger = getLogger(__name__)
logger.setLevel(INFO)


class FFGetResult(Enum):
    """Core.run の結果を表す列挙型

    Attributes:
        SUCCESS (auto): 成功時
        FAILED (auto): 失敗時
    """
    SUCCESS = auto()
    FAILED = auto()


@dataclass(frozen=True)
class Core():
    """ffgetter のメイン実行機能を司るクラス

    Args:
        None

    Attributes:
        config (configparser.ConfigParser): config 設定
        twitter_api (TwitterAPI): ツイッターAPI使用クラス
        CONFIG_FILE_PATH (str): config 設定ファイルがあるパス
    """
    parser: argparse.ArgumentParser | None = None
    config: ClassVar[configparser.ConfigParser]
    twitter_api: ClassVar[TwitterAPI]

    CONFIG_FILE_PATH = "./config/config.ini"

    def __post_init__(self) -> None:
        """初期化後処理
        """
        work_directory: Path = Path(os.path.dirname(__file__)).parent
        os.chdir(work_directory)

        config = configparser.ConfigParser()
        config.read_file(Path(self.CONFIG_FILE_PATH).open("r", encoding="utf-8"))
        if self.parser:
            args = self.parser.parse_args()
            if args.reply_to_user_name:
                config["notification"]["is_notify"] = "True"
                config["notification"]["reply_to_user_name"] = ScreenName(args.reply_to_user_name).name
            if args.disable_after_open:
                config["after_open"]["is_after_open"] = "False"
            if args.reserved_file_num:
                config["move_old_file"]["is_move_old_file"] = "True"
                config["move_old_file"]["reserved_file_num"] = str(args.reserved_file_num)
        object.__setattr__(self, "config", config)

        config_twitter_token = config["twitter_token_keys_v2"]
        API_KEY = config_twitter_token["api_key"]
        API_KEY_SECRET = config_twitter_token["api_key_secret"]
        ACCESS_TOKEN_KEY = config_twitter_token["access_token"]
        ACCESS_TOKEN_SECRET = config_twitter_token["access_token_secret"]

        twitter_api = TwitterAPI(
            API_KEY,
            API_KEY_SECRET,
            ACCESS_TOKEN_KEY,
            ACCESS_TOKEN_SECRET
        )
        object.__setattr__(self, "twitter_api", twitter_api)

    def run(self) -> FFGetResult:
        """ffgetter メイン実行

        (1)ユーザIDを取得し、following と follower リストを TwitterAPI を通して取得する
        (2)前回記録した following と follower を前回実行ファイルから取得する(prev_*)
        (3)今回のffと前回のffを比較し、その差分を取得する(diff_*)
        (4)結果をファイルに記録・保存する
        (5)完了通知を送信する
        (6)古いファイルを移動させる
        (7)完了後にファイルを開く

        Args:
            None

        Returns:
            FFGetResult: 成功時SUCCESS, 失敗時FAILED
        """
        try:
            # (1)TwitterAPI を使用してffを取得
            following_list = None
            follower_list = None
            if self.config["twitter_noapi"].getboolean("is_twitter_noapi"):
                username = self.config["twitter_noapi"]["username"]
                password = self.config["twitter_noapi"]["password"]
                target_username = self.config["twitter_noapi"]["target_username"]

                following_fetcher = NoAPIFollowingFetcher(username, password, target_username)
                following_list = following_fetcher.fetch()
                follower_fetcher = NoAPIFollowerFetcher(username, password, target_username)
                follower_list = follower_fetcher.fetch()
            else:
                user_id = self.twitter_api.get_user_id()
                following_list = self.twitter_api.get_following(user_id)
                follower_list = self.twitter_api.get_follower(user_id)

            # (2)前回実行ファイルより前回のffを取得
            directory = Directory()
            prev_following_list = directory.get_last_following()
            prev_follower_list = directory.get_last_follower()

            # (3)差分取得
            diff_following_list = DiffFollowingList.create_from_diff(following_list, prev_following_list)
            diff_follower_list = DiffFollowerList.create_from_diff(follower_list, prev_follower_list)

            # (4)結果保存
            saved_file_path = directory.save_file(following_list, follower_list, diff_following_list, diff_follower_list)
            logger.info(f"file saved to {str(saved_file_path)}.")

            # (5)完了通知
            done_msg = "FFGetter run.\n"
            done_msg += datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            done_msg += " Process Done.\n"
            done_msg += f"follow num : {len(following_list)} , "
            done_msg += f"follower num : {len(follower_list)}\n"

            try:
                tweet_str = ""
                is_notify = self.config["notification"].getboolean("is_notify")
                reply_user_name = self.config["notification"]["reply_to_user_name"]
                if is_notify and (reply_user_name != ""):
                    tweet_str = "@" + reply_user_name + " " + done_msg
                    if self.twitter_api.post_tweet(tweet_str):
                        logger.info("Reply posted.")
            except Exception:
                logger.info("Reply post failed.")

            logger.info("")
            logger.info(done_msg)

            # (6)古いファイルを移動させる
            is_move_old_file = self.config["move_old_file"].getboolean("is_move_old_file")
            if is_move_old_file:
                reserved_file_num = int(self.config["move_old_file"]["reserved_file_num"])
                directory.move_old_file(reserved_file_num)

            # (7)完了後にファイルを開く
            is_after_open = self.config["after_open"].getboolean("is_after_open")
            if is_after_open:
                subprocess.Popen(["start", str(saved_file_path)], shell=True)

        except Exception as e:
            logger.error(e)
            return FFGetResult.FAILED
        return FFGetResult.SUCCESS


if __name__ == "__main__":
    import logging.config
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    for name in logging.root.manager.loggerDict:
        if "ffgetter" not in name:
            getLogger(name).disabled = True
    core = Core()
    logger.info(core.run())
