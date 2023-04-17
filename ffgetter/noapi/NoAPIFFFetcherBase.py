# coding: utf-8
import asyncio
import json
import pprint
import random
import shutil
from logging import INFO, getLogger
from pathlib import Path
from typing import Literal

from pyppeteer.page import Page
from requests.models import Response
from requests_html import HTML

from ffgetter.noapi.Password import Password
from ffgetter.noapi.TwitterSession import TwitterSession
from ffgetter.noapi.Username import Username
from ffgetter.value_object.UserRecord import Follower, Following
from ffgetter.value_object.UserRecordList import FollowerList, FollowingList

logger = getLogger(__name__)
logger.setLevel(INFO)


class NoAPIFFFetcherBase():
    username: Username
    password: Password
    target_username: Username
    ff_type: Literal["following", "follower"]
    twitter_session: TwitterSession
    redirect_urls: list[str]
    content_list: list[str]

    def __init__(self, username: Username | str, password: Password | str, target_username: Username | str, ff_type: Literal["following", "follower"]) -> None:
        if isinstance(username, str):
            username = Username(username)
        if isinstance(password, str):
            password = Password(password)
        if isinstance(target_username, str):
            target_username = Username(target_username)

        if not (isinstance(username, Username) and username.name != ""):
            raise ValueError("username is not Username or empty.")
        if not (isinstance(password, Password) and password.password != ""):
            raise ValueError("password is not Password or empty.")
        if not (isinstance(target_username, Username) and target_username.name != ""):
            raise ValueError("password is not Username or empty.")
        if not (isinstance(ff_type, str) and (ff_type in ["following", "follower"])):
            raise ValueError('ff_type is not Literal["following", "follower"].')

        self.username = username
        self.password = password
        self.target_username = target_username
        self.ff_type = ff_type
        self.twitter_session = TwitterSession.create(username=username, password=password)
        self.redirect_urls = []
        self.content_list = []

    @property
    def cache_path(self) -> Path:
        # キャッシュファイルパス
        return Path(__file__).parent / f"cache/{self.ff_type}/"

    @property
    def fetch_url(self) -> str:
        if self.ff_type == "following":
            return self.twitter_session.FOLLOWING_TEMPLATE.format(self.target_username.name)
        elif self.ff_type == "follower":
            return self.twitter_session.FOLLOWER_TEMPLATE.format(self.target_username.name)
        raise ValueError("fetch_url is invalid.")

    async def _response_listener(self, response: Response) -> None:
        base_path = Path(self.cache_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # レスポンス監視用リスナー
        if self.ff_type in response.url.lower():
            # レスポンスが ff_type 関連ならば
            self.redirect_urls.append(response.url)
            if "application/json" in response.headers.get("content-type", ""):
                # レスポンスがJSONならばキャッシュに保存
                content = await response.json()
                n = len(self.content_list)
                with Path(base_path / f"content_cache{n}.txt").open("w", encoding="utf8") as fout:
                    json.dump(content, fout)
                self.content_list.append(content)

    async def fetch_jsons(self, max_scroll: int = 40, each_scroll_wait: float = 1.5) -> list[dict]:
        """ff_type ページをクロールしてロード時のJSONをキャプチャする

        Args:
            max_scroll (int): 画面スクロールの最大回数. デフォルトは40[回].
            each_scroll_wait (float): それぞれの画面スクロール時に待つ秒数. デフォルトは1.5[s].

        Notes:
            対象URLは "https://twitter.com/{self.target_username.name}/{self.ff_type}"
                (self.twitter_session.FOLLOWING_TEMPLATE.format(self.target_username.name))
            実行には少なくとも max_scroll * each_scroll_wait [s] 秒かかる
            キャッシュは self.TWITTER_CACHE_PATH に保存される

        Returns:
            list[dict]: ツイートオブジェクトを表すJSONリスト
        """
        logger.info(f"Fetched {self.ff_type} by No API -> start")

        # セッション使用準備
        await self.twitter_session.prepare()
        logger.info("Session use prepared.")

        # fetch_url ページに遷移
        # スクロール操作を行うため、pageを保持しておく
        res = await self.twitter_session.get(self.fetch_url)
        await res.html.arender(keep_page=True)
        html: HTML = res.html
        page: Page = html.page
        logger.info(f"Opening {self.ff_type} page is success.")

        # キャッシュ保存場所の準備
        self.redirect_urls = []
        self.content_list = []
        base_path = Path(self.cache_path)
        if base_path.is_dir():
            shutil.rmtree(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # レスポンス監視用リスナー
        page.on("response", lambda response: asyncio.ensure_future(self._response_listener(response)))

        # スクロール時の待ち秒数をランダムに生成するメソッド
        def get_wait_millisecond() -> float:
            pn = (random.random() - 0.5) * 1.0  # [-0.5, 0.5)
            candidate_sec = (pn + each_scroll_wait) * 1000.0
            return float(max(candidate_sec, 1000.0))  # [1000.0, 2000.0)

        # ff_type ページをスクロールして読み込んでいく
        # ページ下部に達した時に次のツイートが読み込まれる
        # このときレスポンス監視用リスナーがレスポンスをキャッチする
        # TODO::終端までスクロールしたことを検知する
        logger.info(f"Getting {self.ff_type} page fetched -> start")
        for i in range(max_scroll):
            await page.evaluate("""
                () => {
                    let elm = document.documentElement;
                    let bottom = elm.scrollHeight - elm.clientHeight;
                    window.scroll(0, bottom);
                }
            """)
            await page.waitFor(
                get_wait_millisecond()
            )
            logger.info(f"({i+1}/{max_scroll}) pages fetched.")
        await page.waitFor(2000)
        logger.info(f"Getting {self.ff_type} page fetched -> done")

        # リダイレクトURLをキャッシュに保存
        if self.redirect_urls:
            with Path(base_path / "redirect_urls.txt").open("w", encoding="utf8") as fout:
                fout.write(pprint.pformat(self.redirect_urls))

        # キャッシュから読み込み
        # content_list と result はほぼ同一の内容になる
        # 違いは result は json.dump→json.load したときに、エンコード等が吸収されていること
        result: list[dict] = []
        for i, content in enumerate(self.content_list):
            with Path(base_path / f"content_cache{i}.txt").open("r", encoding="utf8") as fin:
                json_dict = json.load(fin)
                result.append(json_dict)

        logger.info(f"Fetched {self.ff_type} by No API -> done")
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
        fetched_jsons = self.twitter_session.loop.run_until_complete(self.fetch_jsons())
        result = self.to_convert(fetched_jsons)
        # pprint.pprint(len(result))
        return result


class NoAPIFollowingFetcher(NoAPIFFFetcherBase):
    def __init__(self, username: Username | str, password: Password | str, target_username: Username | str) -> None:
        super().__init__(username, password, target_username, "following")


class NoAPIFollowerFetcher(NoAPIFFFetcherBase):
    def __init__(self, username: Username | str, password: Password | str, target_username: Username | str) -> None:
        super().__init__(username, password, target_username, "follower")


if __name__ == "__main__":
    import configparser
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_noapi"]
    username = config["username"]
    password = config["password"]
    target_username = config["target_username"]

    # キャッシュから読み込み
    # base_path = Path(fetcher.TWITTER_CACHE_PATH)
    # fetched_json = []
    # for cache_path in base_path.glob("*content_cache*"):
    #     with cache_path.open("r", encoding="utf8") as fin:
    #         json_dict = json.load(fin)
    #         fetched_json.append(json_dict)

    fetcher = NoAPIFollowingFetcher(Username(username), Password(password), Username(target_username))
    following_list = fetcher.fetch()
    pprint.pprint(len(following_list))

    fetcher = NoAPIFollowerFetcher(Username(username), Password(password), Username(target_username))
    follower_list = fetcher.fetch()
    pprint.pprint(len(follower_list))
