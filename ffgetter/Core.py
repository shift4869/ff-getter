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

from plyer import notification

from ffgetter.Directory import Directory
from ffgetter.LogMessage import Message as Msg
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


@dataclass()
class Core():
    """ffgetter のメイン実行機能を司るクラス

    Args:
        parser (argparse.ArgumentParser): ArgumentParser インスタンス, デフォルトはNone

    Attributes:
        parser (argparse.ArgumentParser): ArgumentParser インスタンス
        config (configparser.ConfigParser): config 設定
        CONFIG_FILE_PATH (str): config 設定ファイルがあるパス
    """
    parser: argparse.ArgumentParser | None = None
    config: ClassVar[configparser.ConfigParser]

    CONFIG_FILE_PATH = "./config/config.ini"

    def __post_init__(self) -> None:
        """初期化後処理
        """
        logger.info(Msg.CORE_INIT_START())
        work_directory: Path = Path(os.path.dirname(__file__)).parent
        os.chdir(work_directory)
        logger.info(Msg.SET_CURRENT_DIRECTORY().format(str(work_directory)))

        config = configparser.ConfigParser()
        config.read_file(Path(self.CONFIG_FILE_PATH).open("r", encoding="utf-8"))
        if self.parser:
            args = self.parser.parse_args()
            if args.disable_notification:
                config["notification"]["is_notify"] = "False"
            if args.disable_after_open:
                config["after_open"]["is_after_open"] = "False"
            if args.reserved_file_num:
                config["move_old_file"]["is_move_old_file"] = "True"
                config["move_old_file"]["reserved_file_num"] = str(args.reserved_file_num)
        self.config = config
        logger.info(Msg.CORE_INIT_DONE())

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
        logger.info(Msg.CORE_RUN_START())
        try:
            # (1)NoAPIでffを取得
            following_list = None
            follower_list = None
            logger.info(Msg.NO_API_MODE())
            username = self.config["twitter_noapi"]["username"]
            password = self.config["twitter_noapi"]["password"]
            target_username = self.config["twitter_noapi"]["target_username"]

            logger.info(Msg.GET_FOLLOWING_LIST_START())
            following_fetcher = NoAPIFollowingFetcher(username, password, target_username)
            following_list = following_fetcher.fetch()
            logger.info(Msg.GET_FOLLOWING_LIST_DONE())

            logger.info(Msg.GET_FOLLOWER_LIST_START())
            follower_fetcher = NoAPIFollowerFetcher(username, password, target_username)
            follower_list = follower_fetcher.fetch()
            logger.info(Msg.GET_FOLLOWER_LIST_DONE())

            # (2)前回実行ファイルより前回のffを取得
            logger.info(Msg.DIRECTORY_INIT_START())
            directory = Directory()
            logger.info(Msg.SET_CURRENT_DIRECTORY().format(str(directory.base_path)))
            logger.info(Msg.DIRECTORY_INIT_DONE())

            logger.info(Msg.GET_PREV_FOLLOWING_LIST_START())
            prev_following_list = directory.get_last_following()
            logger.info(Msg.GET_PREV_FOLLOWING_LIST_DONE())

            logger.info(Msg.GET_PREV_FOLLOWER_LIST_START())
            prev_follower_list = directory.get_last_follower()
            logger.info(Msg.GET_PREV_FOLLOWER_LIST_DONE())

            # (3)差分取得
            logger.info(Msg.GET_DIFF_FOLLOWING_LIST_START())
            diff_following_list = DiffFollowingList.create_from_diff(following_list, prev_following_list)
            logger.info(Msg.GET_DIFF_FOLLOWING_LIST_DONE())

            logger.info(Msg.GET_DIFF_FOLLOWER_LIST_START())
            diff_follower_list = DiffFollowerList.create_from_diff(follower_list, prev_follower_list)
            logger.info(Msg.GET_DIFF_FOLLOWER_LIST_DONE())

            # (4)結果保存
            logger.info(Msg.SAVE_RESULT_START())
            saved_file_path = directory.save_file(following_list, follower_list, diff_following_list, diff_follower_list)
            logger.info(f"file saved to {str(saved_file_path)}.")
            logger.info(Msg.SAVE_RESULT_DONE())

            # (5)完了通知
            done_msg = "FFGetter run.\n"
            done_msg += datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            done_msg += " Process Done.\n"
            done_msg += f"follow num : {len(following_list)} , "
            done_msg += f"follower num : {len(follower_list)}\n"

            try:
                is_notify = self.config["notification"].getboolean("is_notify")
                if is_notify:
                    notification.notify(
                        title="ffgetter",
                        message=done_msg,
                    )
            except Exception:
                # logger.info("Reply post failed.")
                logger.info("Notification failed.")

            logger.info("")
            logger.info(done_msg)

            # (6)古いファイルを移動させる
            is_move_old_file = self.config["move_old_file"].getboolean("is_move_old_file")
            if is_move_old_file:
                logger.info(Msg.MOVE_OLD_FILE_START())
                reserved_file_num = int(self.config["move_old_file"]["reserved_file_num"])
                moved_list = directory.move_old_file(reserved_file_num)
                if moved_list:
                    moved_file_list = [str(f) for f in moved_list]
                    logger.info(Msg.MOVE_OLD_FILE_PATH().format(",".join(moved_file_list) + "."))
                else:
                    logger.info(Msg.MOVE_OLD_FILE_PATH().format("No File moved."))
                logger.info(Msg.MOVE_OLD_FILE_DONE())

            # (7)完了後にファイルを開く
            is_after_open = self.config["after_open"].getboolean("is_after_open")
            if is_after_open:
                subprocess.Popen(["start", str(saved_file_path)], shell=True)
                logger.info(Msg.RESULT_FILE_OPENING().format(str(saved_file_path)))

        except Exception as e:
            logger.error(e)
            return FFGetResult.FAILED
        logger.info(Msg.CORE_RUN_DONE())
        return FFGetResult.SUCCESS


if __name__ == "__main__":
    import logging.config
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    for name in logging.root.manager.loggerDict:
        if "ffgetter" not in name:
            getLogger(name).disabled = True
    core = Core()
    logger.info(core.run())
