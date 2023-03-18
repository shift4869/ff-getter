# coding: utf-8
import json
import logging.config
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from logging import INFO, getLogger
from pathlib import Path
from typing import ClassVar

import requests
from requests_oauthlib import OAuth1Session

from ffgetter.value_object.UserId import UserId
from ffgetter.value_object.UserRecord import Follower, Following
from ffgetter.value_object.UserRecordList import FollowerList, FollowingList

logger = getLogger(__name__)
logger.setLevel(INFO)


class TwitterAPIEndpoint(Enum):
    USER_LOOKUP_ME = "https://api.twitter.com/2/users/me"
    FOLLOWING = "https://api.twitter.com/2/users/{}/following"
    FOLLOWERS = "https://api.twitter.com/2/users/{}/followers"
    POST_TWEET = "https://api.twitter.com/2/tweets"


@dataclass
class TwitterAPI():
    api_key: str
    api_secret: str
    access_token_key: str
    access_token_secret: str
    oauth: ClassVar[OAuth1Session]

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str):
            raise TypeError("api_key must be str.")
        if not isinstance(self.api_secret, str):
            raise TypeError("api_secret must be str.")
        if not isinstance(self.access_token_key, str):
            raise TypeError("access_token_key must be str.")
        if not isinstance(self.access_token_secret, str):
            raise TypeError("access_token_secret must be str.")

        self.oauth = OAuth1Session(
            self.api_key,
            self.api_secret,
            self.access_token_key,
            self.access_token_secret
        )

        # 疎通確認
        url = TwitterAPIEndpoint.USER_LOOKUP_ME.value
        res = self.get(url)  # 失敗時は例外が送出される

    def _wait(self, dt_unix: float) -> None:
        """指定UNIX時間まで待機する

        Args:
            dt_unix (float): UNIX時間の指定（秒）
        """
        seconds = dt_unix - time.mktime(datetime.now().timetuple())
        seconds = max(seconds, 0)
        logger.debug("=======================")
        logger.debug(f"=== waiting {seconds} sec ===")
        logger.debug("=======================")
        sys.stdout.flush()
        time.sleep(seconds)

    def _wait_until_reset(self, response: dict) -> None:
        """TwitterAPIが利用できるまで待つ

        Args:
            response (dict): 利用できるまで待つTwitterAPIを使ったときのレスポンス

        Raises:
            HTTPError: レスポンスヘッダにx-rate-limit-remaining and x-rate-limit-reset が入ってない場合

        Returns:
            None: このメソッド実行後はresponseに対応するエンドポイントが利用可能であることが保証される
        """
        match response.headers:
            case {
                # "x-rate-limit-limit": limit,
                "x-rate-limit-remaining": remain_count,
                "x-rate-limit-reset": dt_unix,
            }:
                remain_count = int(remain_count)
                dt_unix = float(dt_unix)
                dt_jst_aware = datetime.fromtimestamp(dt_unix, timezone(timedelta(hours=9)))
                remain_seconds = dt_unix - time.mktime(datetime.now().timetuple())
                logger.debug("リクエストURL {}".format(response.url))
                logger.debug("アクセス可能回数 {}".format(remain_count))
                logger.debug("リセット時刻 {}".format(dt_jst_aware))
                logger.debug("リセットまでの残り時間 {}[s]".format(remain_seconds))
                if remain_count == 0:
                    self._wait(dt_unix + 3)
            case _:
                msg = "not found  -  x-rate-limit-remaining and x-rate-limit-reset"
                logger.debug(msg)
                raise requests.HTTPError(msg)

    def request(self, endpoint_url: str, params: dict, method: str) -> dict:
        """TwitterAPIを使用するラッパメソッド

        Args:
            endpoint_url (str): TwitterAPIエンドポイントURL
            params (dict): TwitterAPI使用時に渡すパラメータ
            method (str): TwitterAPI使用時のメソッド、デフォルトはGET

        Raises:
            ValueError: endpoint_url が想定外のエンドポイントの場合
            ValueError: method が想定外のメソッドの場合
            ValueError: 月のツイートキャップ上限対象APIで、上限を超えている場合
            HTTPError: RETRY_NUM=5回リトライしてもAPI利用結果が200でなかった場合

        Returns:
            dict: TwitterAPIレスポンス
        """
        # バリデーション
        if not isinstance(endpoint_url, str):
            raise ValueError("endpoint_url must be str.")
        if not isinstance(params, dict):
            raise ValueError("params must be dict.")
        if not (isinstance(method, str) and method in ["GET", "POST", "PUT", "DELETE"]):
            raise ValueError('method must be in ["GET", "POST", "PUT", "DELETE"].')

        # メソッド振り分け
        method_func = None
        if method == "GET":
            method_func = self.oauth.get
        elif method == "POST":
            method_func = self.oauth.post
        elif method == "DELETE":
            method_func = self.oauth.delete
        if not method_func:
            raise ValueError(f"{method} is invalid method.")

        # RETRY_NUM 回だけリクエストを試行する
        RETRY_NUM = 5
        for i in range(RETRY_NUM):
            try:
                # POSTの場合はjsonとして送信（ヘッダーにjson指定すればOK?）
                response = None
                if method == "POST":
                    response = method_func(endpoint_url, json=params)
                else:
                    response = method_func(endpoint_url, params=params)
                response.raise_for_status()

                # 成功したならばJSONとして解釈してレスポンスを返す
                res: dict = json.loads(response.text)
                return res
            except requests.exceptions.RequestException as e:
                logger.warning(e.response.text)
            except Exception as e:
                pass

            # リクエスト失敗した場合
            try:
                # レートリミットにかかっていないか確認して必要なら待つ
                self._wait_until_reset(response)
            except Exception as e:
                # 原因不明：徐々に待機時間を増やしてとりあえず待つ(exp backoff)
                wair_seconds = 8 ** i
                n = time.mktime(datetime.now().timetuple())
                self._wait(n + wair_seconds)
            logger.warning(f"retry ({i+1}/{RETRY_NUM}) ...")
        else:
            raise requests.HTTPError("Twitter API error : exceed RETRY_NUM.")

    def get(self, endpoint_url: str, params: dict = {}) -> dict:
        """GETリクエストのエイリアス
        """
        return self.request(endpoint_url=endpoint_url, params=params, method="GET")

    def post(self, endpoint_url: str, params: dict = {}) -> dict:
        """POSTリクエストのエイリアス
        """
        return self.request(endpoint_url=endpoint_url, params=params, method="POST")

    def get_user_id(self) -> UserId:
        """ユーザID取得
        """
        url = TwitterAPIEndpoint.USER_LOOKUP_ME.value
        res = self.get(url, params={})
        user_id = res.get("data", {}).get("id", "")
        if not user_id:
            raise ValueError(f"user_id getting failed : \n{res}")
        user_id_num = int(user_id)
        return UserId(user_id_num)

    def get_following(self, user_id: UserId) -> FollowingList:
        """フォローしているユーザを取得
        """
        MAX_RESULTS = 1000
        url = TwitterAPIEndpoint.FOLLOWING.value.format(user_id.id)
        next_token = ""
        following_list = []
        while True:
            params = {
                "max_results": MAX_RESULTS
            }
            if next_token != "":
                params["pagination_token"] = next_token
            data_dict = self.get(url, params=params)

            data_list = data_dict.get("data", [])
            following_data_list = [
                Following.create(
                    data.get("id"),
                    data.get("name"),
                    data.get("username"),
                )
                for data in data_list
            ]
            following_list.extend(following_data_list)

            next_token = data_dict.get("meta", {}).get("next_token", "")
            if next_token == "":
                break
        return FollowingList.create(following_list)

    def get_follower(self, user_id: UserId) -> FollowerList:
        """フォローされているユーザを取得
        """
        MAX_RESULTS = 1000
        url = TwitterAPIEndpoint.FOLLOWERS.value.format(user_id.id)
        next_token = ""
        follower_list = []
        while True:
            params = {
                "max_results": MAX_RESULTS
            }
            if next_token != "":
                params["pagination_token"] = next_token
            data_dict = self.get(url, params=params)

            data_list = data_dict.get("data", [])
            follower_data_list = [
                Follower.create(
                    data.get("id"),
                    data.get("name"),
                    data.get("username"),
                )
                for data in data_list
            ]
            follower_list.extend(follower_data_list)

            next_token = data_dict.get("meta", {}).get("next_token", "")
            if next_token == "":
                break
        return FollowerList.create(follower_list)

    def post_tweet(self, tweet_str: str) -> dict:
        """ツイートをポストする

        Args:
            tweet_str (str): ポストする文字列

        Returns:
            response (dict): post後のレスポンス
        """
        url = TwitterAPIEndpoint.POST_TWEET.value
        params = {
            "text": tweet_str,
        }
        response = self.post(url, params=params)
        return response


if __name__ == "__main__":
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    for name in logging.root.manager.loggerDict:
        if __name__ not in name:
            getLogger(name).disabled = True

    import configparser
    config = configparser.ConfigParser()
    config.read_file(Path("./config/config.ini").open("r", encoding="utf-8"))
    config_twitter_token = config["twitter_token_keys_v2"]
    API_KEY = config_twitter_token["api_key"]
    API_KEY_SECRET = config_twitter_token["api_key_secret"]
    ACCESS_TOKEN_KEY = config_twitter_token["access_token"]
    ACCESS_TOKEN_SECRET = config_twitter_token["access_token_secret"]

    twitter_api = TwitterAPI(API_KEY, API_KEY_SECRET, ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET)
    print(twitter_api)

    # ユーザID取得
    user_id = twitter_api.get_user_id()
    print(user_id)
