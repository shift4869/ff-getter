# coding: utf-8
import json
import pprint
import shutil
from logging import INFO, getLogger
from pathlib import Path
from typing import Literal

from twitter.scraper import Scraper

from ffgetter.noapi.Username import Username
from ffgetter.value_object.UserRecord import Follower, Following
from ffgetter.value_object.UserRecordList import FollowerList, FollowingList

logger = getLogger(__name__)
logger.setLevel(INFO)


class NoAPIFFFetcherBase():
    ct0: str
    auth_token: str
    target_screen_name: Username
    target_id: int
    ff_type: Literal["following", "follower"]

    def __init__(self, ct0: str, auth_token: str, target_screen_name: str, target_id: int, ff_type: Literal["following", "follower"]) -> None:
        target_id = int(target_id)

        if not isinstance(ct0, str):
            raise ValueError("ct0 is not str.")
        if not isinstance(auth_token, str):
            raise ValueError("auth_token is not str.")
        if not isinstance(target_screen_name, str):
            raise ValueError("target_screen_name is not str.")
        if not isinstance(target_id, int):
            raise ValueError("target_id is not int.")
        if not (isinstance(ff_type, str) and (ff_type in ["following", "follower"])):
            raise ValueError('ff_type is not Literal["following", "follower"].')

        self.ct0 = ct0
        self.auth_token = auth_token
        self.target_screen_name = target_screen_name
        self.target_id = target_id
        self.ff_type = ff_type

    @property
    def cache_path(self) -> Path:
        # キャッシュファイルパス
        return Path(__file__).parent / f"cache/{self.ff_type}/"

    def fetch_jsons(self, max_scroll: int = 40, each_scroll_wait: float = 1.5) -> list[dict]:
        logger.info(f"Fetched {self.ff_type} by TAC -> start")

        # キャッシュ保存場所の準備
        base_path = Path(self.cache_path)
        if base_path.is_dir():
            shutil.rmtree(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # ff_type ページをスクロールして読み込んでいく
        # ページ下部に達した時に次のツイートが読み込まれる
        # このときレスポンス監視用リスナーがレスポンスをキャッチする
        # TODO::終端までスクロールしたことを検知する
        logger.info(f"Getting {self.ff_type} fetched -> start")
        scraper = Scraper(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
        fetched_contents = []
        if self.ff_type == "following":
            fetched_contents = scraper.following([self.target_id])
        elif self.ff_type == "follower":
            fetched_contents = scraper.followers([self.target_id])
        logger.info(f"Getting {self.ff_type} fetched -> done")

        # キャッシュに保存
        for i, content in enumerate(fetched_contents):
            Path(base_path / f"content_cache{i}.txt").write_text(
                json.dumps(content, indent=4), encoding="utf-8"
            )

        # キャッシュから読み込み
        # content_list と result はほぼ同一の内容になる
        # 違いは result は json.dump→json.load したときに、エンコード等が吸収されていること
        result: list[dict] = []
        for i, content in enumerate(fetched_contents):
            with Path(base_path / f"content_cache{i}.txt").open("r", encoding="utf8") as fin:
                json_dict = json.load(fin)
                result.append(json_dict)

        logger.info(f"Fetched {self.ff_type} by TAC -> done")
        return result

    def interpret_json(self, json_dict: dict) -> dict:
        """辞書構成をたどる
        """
        if not isinstance(json_dict, dict):
            raise TypeError("argument tweet is not dict.")

        match json_dict:
            case {
                "content": {
                    "itemContent": {
                        "user_results": {
                            "result": result
                        }
                    },
                },
            }:
                id_str = result.get("rest_id", "")
                name = result.get("legacy", {}).get("name", "")
                screen_name = result.get("legacy", {}).get("screen_name", "")
                return {
                    "id_str": id_str,
                    "name": name,
                    "screen_name": screen_name,
                }
        return {}

    def to_convert(self, fetched_jsons: list[dict]) -> FollowingList | FollowerList:
        if not isinstance(fetched_jsons, list):
            return []
        if not isinstance(fetched_jsons[0], dict):
            return []

        # 辞書パース
        data_list: list[Following] | list[Follower] = []
        for r in fetched_jsons:
            instructions = r.get("data", {}) \
                            .get("user", {}) \
                            .get("result", {}) \
                            .get("timeline", {}) \
                            .get("timeline", {}) \
                            .get("instructions", [{}])
            if not instructions:
                continue
            for instruction in instructions:
                entries: list[dict] = instruction.get("entries", [])
                if not entries:
                    continue
                for entry in entries:
                    data_dict = self.interpret_json(entry)
                    if not data_dict:
                        continue
                    if self.ff_type == "following":
                        ff_data = Following.create(
                            data_dict.get("id_str", ""),
                            data_dict.get("name", ""),
                            data_dict.get("screen_name", ""),
                        )
                    elif self.ff_type == "follower":
                        ff_data = Follower.create(
                            data_dict.get("id_str", ""),
                            data_dict.get("name", ""),
                            data_dict.get("screen_name", ""),
                        )
                    data_list.append(ff_data)
        if not data_list:
            # 辞書パースエラー or 1件も無かった
            return []

        if self.ff_type == "following":
            return FollowingList.create(data_list)
        elif self.ff_type == "follower":
            return FollowerList.create(data_list)
        return []

    def fetch(self) -> FollowingList | FollowerList:
        fetched_jsons = self.fetch_jsons()
        result = self.to_convert(fetched_jsons)
        # pprint.pprint(len(result))
        return result


class NoAPIFollowingFetcher(NoAPIFFFetcherBase):
    def __init__(self, ct0: str, auth_token: str, target_screen_name: str, target_id: int) -> None:
        super().__init__(ct0, auth_token, target_screen_name, target_id, "following")


class NoAPIFollowerFetcher(NoAPIFFFetcherBase):
    def __init__(self, ct0: str, auth_token: str, target_screen_name: str, target_id: int) -> None:
        super().__init__(ct0, auth_token, target_screen_name, target_id, "follower")


if __name__ == "__main__":
    import configparser
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_api_client"]
    ct0 = config["ct0"]
    auth_token = config["auth_token"]
    target_screen_name = config["target_screen_name"]
    target_id = config["target_id"]

    # キャッシュから読み込み
    # base_path = Path(fetcher.TWITTER_CACHE_PATH)
    # fetched_json = []
    # for cache_path in base_path.glob("*content_cache*"):
    #     with cache_path.open("r", encoding="utf8") as fin:
    #         json_dict = json.load(fin)
    #         fetched_json.append(json_dict)

    fetcher = NoAPIFollowingFetcher(ct0, auth_token, target_screen_name, target_id)
    following_list = fetcher.fetch()
    pprint.pprint(len(following_list))

    fetcher = NoAPIFollowerFetcher(ct0, auth_token, target_screen_name, target_id)
    follower_list = fetcher.fetch()
    pprint.pprint(len(follower_list))
