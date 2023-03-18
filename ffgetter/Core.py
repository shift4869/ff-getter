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
    SUCCESS = auto()
    FAILED = auto()


@dataclass(frozen=True)
class Core():
    config: ClassVar[configparser.ConfigParser]
    twitter_api: ClassVar[TwitterAPI]

    FILE_NAME_BASE = "ff_list"

    def __post_init__(self) -> None:
        work_directory: Path = Path(os.path.dirname(__file__)).parent
        os.chdir(work_directory)

        config = configparser.ConfigParser()
        config.read_file(Path("./config/config.ini").open("r", encoding="utf-8"))
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
        user_id = self.twitter_api.get_user_id()
        following_list = self.twitter_api.get_following(user_id)
        follower_list = self.twitter_api.get_follower(user_id)

        directory = Directory()
        prev_following_list = directory.get_last_following()
        prev_follower_list = directory.get_last_follower()

        diff_following_list = DiffFollowingList.create_from_diff(following_list, prev_following_list)
        diff_follower = DiffFollowerList.create_from_diff(follower_list, prev_follower_list)

        saved_text = directory.save_file(following_list, follower_list, diff_following_list, diff_follower)
        print(saved_text)

        # 完了リプライ通知を送信
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

        print("")
        if reply_user_name != "":
            if self.twitter_api.post_tweet(tweet_str):
                print("Reply posted.")
            else:
                print("Reply post failed.")

        print(done_msg)
        return FFGetResult.SUCCESS


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    for name in logging.root.manager.loggerDict:
        if __name__ not in name:
            getLogger(name).disabled = True
    core = Core()
    print(core.run())
