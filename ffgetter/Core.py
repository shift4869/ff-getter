# coding: utf-8
import configparser
import datetime
import logging.config
import os
from dataclasses import dataclass
from enum import Enum, auto
from logging import INFO, getLogger
from pathlib import Path
from typing import ClassVar

from ffgetter.Directory import Directory
from ffgetter.TwitterAPI import TwitterAPI
from ffgetter.value_object.DiffRecordList import DiffFollowerList, DiffFollowingList

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

        Args:
            None

        Returns:
            FFGetResult: 成功時SUCCESS, 失敗時FAILED
        """
        try:
            # (1)TwitterAPI を使用してffを取得
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
            saved_text = directory.save_file(following_list, follower_list, diff_following_list, diff_follower_list)
            logger.info(saved_text)

            # (5)完了通知
            done_msg = "FFGetter run.\n"
            done_msg += datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            done_msg += " Process Done.\n"
            done_msg += f"follow num : {len(following_list)} , "
            done_msg += f"follower num : {len(follower_list)}\n"

            tweet_str = ""
            try:
                reply_user_name = self.config["notification"]["reply_to_user_name"]
                if reply_user_name == "":
                    tweet_str = done_msg
                else:
                    tweet_str = "@" + reply_user_name + " " + done_msg
            except Exception:
                tweet_str = done_msg

            logger.info("")
            if reply_user_name != "":
                if self.twitter_api.post_tweet(tweet_str):
                    logger.info("Reply posted.")
                else:
                    logger.info("Reply post failed.")

            logger.info(done_msg)
        except Exception as e:
            logger.error(e)
            return FFGetResult.FAILED
        return FFGetResult.SUCCESS


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    for name in logging.root.manager.loggerDict:
        if __name__ not in name:
            getLogger(name).disabled = True
    core = Core()
    logger.info(core.run())
