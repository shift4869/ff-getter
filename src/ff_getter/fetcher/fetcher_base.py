import shutil
from logging import INFO, getLogger
from pathlib import Path

import orjson
from twitter.scraper import Scraper

from ff_getter.util import FFtype, find_values
from ff_getter.value_object.user_name import UserName
from ff_getter.value_object.user_record import Follower, Following
from ff_getter.value_object.user_record_list import FollowerList, FollowingList

logger = getLogger(__name__)
logger.setLevel(INFO)


class FetcherBase:
    ct0: str
    auth_token: str
    target_screen_name: UserName
    target_id: int
    ff_type: FFtype
    is_debug: bool

    def __init__(self, config: dict, ff_type: FFtype, is_debug: False = False) -> None:
        """FetcherBase

        Args:
            config (dict): config.json から取得した設定辞書
            ff_type (FF_Type): "following", "follower" のどちらか
            is_debug (False, optional): デバッグモードかどうか

        Raises:
            ValueError: 引数が不正な値だった場合
        """
        config_twitter_api_client = config["twitter_api_client"]
        match config_twitter_api_client:
            case {
                "ct0": ct0,
                "auth_token": auth_token,
                "target_screen_name": target_screen_name,
                "target_id": target_id,
            }:
                self.ct0 = ct0
                self.auth_token = auth_token
                self.target_screen_name = target_screen_name
                self.target_id = int(target_id)
            case _:
                raise ValueError("config dict is invalid.")

        if not (isinstance(ff_type, FFtype) and ff_type in [FFtype.following, FFtype.follower]):
            raise ValueError("ff_type must be in [FF_Type.following, FF_Type.follower].")
        if not isinstance(is_debug, bool):
            raise ValueError("is_debug must be bool.")

        self.ff_type = ff_type
        self.is_debug = is_debug

    @property
    def cache_path(self) -> Path:
        """キャッシュファイルパス"""
        return Path(__file__).parent / f"cache/{self.ff_type.value}/"

    def fetch_jsons(self) -> list[dict]:
        """fetch

        Returns:
            list[dict]: fetch したff情報辞書を格納したリスト
        """
        logger.info(f"Fetched {self.ff_type.value} by TAC -> start")

        # キャッシュ保存場所の準備
        base_path = Path(self.cache_path)
        if base_path.is_dir() and not self.is_debug:
            shutil.rmtree(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # fetch
        logger.info(f"Getting {self.ff_type.value} fetched -> start")
        fetched_contents: list[dict] = []
        if self.is_debug:
            # キャッシュから読み込み
            cache_file_paths = list(base_path.glob("**/*"))
            if not cache_file_paths:
                raise ValueError(f"cache file not found, {str(base_path.resolve())}.")
            for cache_file_path in cache_file_paths:
                json_dict = orjson.loads(cache_file_path.read_bytes())
                fetched_contents.append(json_dict)
        else:
            scraper = Scraper(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
            if self.ff_type == FFtype.following:
                fetched_contents = scraper.following([self.target_id])
            elif self.ff_type == FFtype.follower:
                fetched_contents = scraper.followers([self.target_id])
        logger.info(f"Getting {self.ff_type.value} fetched -> done")

        # キャッシュに保存
        for i, content in enumerate(fetched_contents):
            Path(base_path / f"content_cache{i}.txt").write_bytes(orjson.dumps(content, option=orjson.OPT_INDENT_2))

        # キャッシュから読み込み
        # content_list と result はほぼ同一の内容になる
        # 違いは result は dump -> load したときに、エンコード等が吸収されていること
        result: list[dict] = []
        for i, content in enumerate(fetched_contents):
            json_dict = orjson.loads(Path(base_path / f"content_cache{i}.txt").read_bytes())
            result.append(json_dict)

        logger.info(f"Fetched {self.ff_type.value} by TAC -> done")
        return result

    def interpret_json(self, json_dict: dict) -> dict:
        """辞書構成をたどる"""
        if not isinstance(json_dict, dict):
            return {}

        match json_dict:
            case {
                "content": {
                    "itemContent": {"user_results": {"result": result}},
                },
            }:
                id_str = result["rest_id"]
                name = result["legacy"]["name"]
                screen_name = result["legacy"]["screen_name"]
                return {
                    "id_str": id_str,
                    "name": name,
                    "screen_name": screen_name,
                }
        return {}

    def to_convert(self, fetched_jsons: list[dict]) -> FollowingList | FollowerList:
        """FollowingList または FollowerList にコンバートする

        Args:
            fetched_jsons (list[dict]): fetch したff情報辞書を格納したリスト

        Returns:
            FollowingList | FollowerList: コンバート後のリストインスタンス
        """
        if not isinstance(fetched_jsons, list):
            return []
        if not all([isinstance(fetched_json, dict) for fetched_json in fetched_jsons]):
            return []

        ToConvertDataClass: type[Following] | type[Follower] = (
            Following if self.ff_type == FFtype.following else Follower
        )
        ToConvertClass: type[FollowingList] | type[FollowerList] = (
            FollowingList if self.ff_type == FFtype.following else FollowerList
        )

        # 辞書パース
        data_list: list[Following] | list[Follower] = []
        for fetched_json in fetched_jsons:
            entries: list[dict] = find_values(fetched_json, "entries", True)
            for entry in entries:
                data_dict = self.interpret_json(entry)
                if not data_dict:
                    continue
                ff_data = ToConvertDataClass.create(
                    data_dict.get("id_str", ""),
                    data_dict.get("name", ""),
                    data_dict.get("screen_name", ""),
                )
                data_list.append(ff_data)
        if not data_list:
            # 辞書パースエラー or 1件も無かった
            return []

        return ToConvertClass.create(data_list)

    def fetch(self) -> FollowingList | FollowerList:
        """fetch

        following か follower かは self.ff_type の値で判定される

        Returns:
            FollowingList | FollowerList: fetch結果のリストインスタンス
        """
        fetched_jsons = self.fetch_jsons()
        result = self.to_convert(fetched_jsons)
        return result


class FollowingFetcher(FetcherBase):
    def __init__(self, config: dict, is_debug: False = False) -> None:
        super().__init__(config, FFtype.following, is_debug)


class FollowerFetcher(FetcherBase):
    def __init__(self, config: dict, is_debug: False = False) -> None:
        super().__init__(config, FFtype.follower, is_debug)


if __name__ == "__main__":
    import logging.config
    import pprint

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.json"
    config = orjson.loads(Path(CONFIG_FILE_NAME).read_bytes())

    fetcher = FollowingFetcher(config, is_debug=True)
    following_list = fetcher.fetch()
    pprint.pprint(len(following_list))

    fetcher = FollowerFetcher(config, is_debug=True)
    follower_list = fetcher.fetch()
    pprint.pprint(len(follower_list))
