import json
import pprint
from logging import INFO, getLogger
from pathlib import Path

from httpx import Response
from twitter.account import Account
from twitter.scraper import Scraper
from twitter.util import get_headers
from twitter.constants import Operation

from following_syncer.util import find_values

logger = getLogger(__name__)
logger.setLevel(INFO)


class TwitterAPI:
    ct0: str
    auth_token: str
    target_screen_name: str

    def __init__(self, ct0: str, auth_token: str, target_screen_name: str) -> None:
        if not isinstance(ct0, str):
            raise TypeError("ct0 must be str.")
        if not isinstance(auth_token, str):
            raise TypeError("auth_token must be str.")
        if not isinstance(target_screen_name, str):
            raise TypeError("target_screen_name must be str.")

        self.ct0 = ct0
        self.auth_token = auth_token
        self.target_screen_name = target_screen_name

    @property
    def scraper(self) -> Scraper:
        if hasattr(self, "_scraper"):
            return self._scraper
        self._scraper = Scraper(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
        return self._scraper

    @property
    def account(self) -> Account:
        if hasattr(self, "_account"):
            return self._account
        self._account = Account(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
        return self._account

    @property
    def target_id(self) -> int:
        if hasattr(self, "_target_id"):
            return self._target_id
        target_user = self.lookup_user_by_screen_name(self.target_screen_name)
        self._target_id = int(find_values(target_user, "rest_id")[0])
        return self._target_id

    def lookup_user_by_screen_name(self, screen_name: str) -> dict:
        logger.info(f"GET user by screen_name, target user is '{screen_name}' -> start")

        # ユーザー情報の問合せ結果はキャッシュする
        if hasattr(self, "_lookup_user_cache"):
            if screen_name in self._lookup_user_cache.keys():
                return self._lookup_user_cache[screen_name]
        else:
            self._lookup_user_cache = {}

        result = self.scraper.users([screen_name])[0]
        self._lookup_user_cache[screen_name] = result

        logger.info(f"GET user by screen_name, target user is '{screen_name}' -> done")
        return result

    def get_likes(self, screen_name: str = "", limit: int = 300, min_id: int = -1) -> list[dict]:
        result = []
        # screen_name が指定されなかった場合 self.target_screen_name を使用する
        screen_name = screen_name or self.target_screen_name

        logger.info(f"GET like, target user is '{screen_name}' -> start")

        target_user = self.lookup_user_by_screen_name(screen_name)
        target_id = int(find_values(target_user, "rest_id")[0])

        likes = self.scraper.likes([target_id], limit=limit)

        # entries のみ対象とする
        entry_lists: list[dict] = find_values(likes, "entries")
        if not entry_lists and len(entry_lists) != 1:
            raise ValueError("Getting Likes is failed or no Likes.")
        tweet_results: list[dict] = find_values(entry_lists, "tweet_results")

        tweet_list = []
        for data_dict in tweet_results:
            # 返信できるアカウントを制限しているときなど階層が異なる場合がある
            if t := data_dict.get("result", {}).get("tweet", {}):
                data_dict: dict = {"result": t}
            if data_dict:
                tweet_list.append(data_dict)
            # min_id が指定されている場合
            if min_id > -1:
                # 現在の id_str を取得して min_id と一致していたら取得を打ち切る
                tweet_ids = find_values(data_dict, "rest_id")
                if str(min_id) in tweet_ids:
                    break

        result = tweet_list[:limit]
        logger.info(f"GET like, target user is '{screen_name}' -> done")
        return result

    def get_user_timeline(self, screen_name: str, limit: int = 300, min_id: int = -1) -> list[dict]:
        result = []
        # screen_name が指定されなかった場合 self.target_screen_name を使用する
        screen_name = screen_name or self.target_screen_name
        logger.info(f"GET user timeline, target user is '{screen_name}' -> start")

        target_user = self.lookup_user_by_screen_name(screen_name)
        target_id = int(find_values(target_user, "rest_id")[0])

        timeline_tweets = self.scraper.tweets_and_replies([target_id], limit=limit)

        # entries のみ対象とする（entry にピン留めツイートの情報があるため除外）
        entry_lists: list[dict] = find_values(timeline_tweets, "entries")
        if not entry_lists and len(entry_lists) != 1:
            raise ValueError("Getting Timeline is failed or no Tweet.")
        tweet_results: list[dict] = find_values(entry_lists, "tweet_results")

        tweet_list = []
        for data_dict in tweet_results:
            # 返信できるアカウントを制限しているときなど階層が異なる場合がある
            if t := data_dict.get("result", {}).get("tweet", {}):
                data_dict: dict = {"result": t}
            if data_dict:
                tweet_list.append(data_dict)
            # min_id が指定されている場合
            if min_id > -1:
                # 現在の id_str を取得して min_id と一致していたら取得を打ち切る
                tweet_ids = find_values(data_dict, "rest_id")
                if str(min_id) in tweet_ids:
                    break

        result = tweet_list[:limit]
        logger.info(f"GET user timeline, target user is '{screen_name}' -> done")
        return result

    def post_tweet(self, tweet_str: str) -> dict:
        logger.info(f"POST tweet -> start")
        result = self.account.tweet(tweet_str)
        logger.info(f"POST tweet -> done")
        return result

    def delete_tweet(self, tweet_id: str) -> dict:
        logger.info(f"DELETE tweet -> start")
        result = self.account.untweet(int(tweet_id))
        logger.info(f"DELETE tweet -> done")
        return result

    def lookup_tweet(self, tweet_id: str) -> dict:
        logger.info(f"GET tweet detail -> start")
        result = self.scraper.tweets_by_id([int(tweet_id)])[0]
        logger.info(f"GET tweet detail -> done")
        return result

    def get_following_list(self) -> list[dict]:
        logger.info(f"GET following list -> start")
        following_users = self.scraper.following([self.target_id])
        result = find_values(following_users, "user_results")
        logger.info(f"GET following list -> done")
        return result

    def get_follower_list(self) -> list[dict]:
        logger.info(f"GET follower list -> start")
        followers_users = self.scraper.followers([self.target_id])
        result = find_values(followers_users, "user_results")
        logger.info(f"GET follower list -> done")
        return result

    def follow(self, user_id: str) -> list[dict]:
        logger.info(f"POST follow -> start")
        result = self.account.follow(int(user_id))
        logger.info(f"POST follow -> done")
        return result

    def remove(self, user_id: str) -> list[dict]:
        logger.info(f"POST remove -> start")
        result = self.account.unfollow(int(user_id))
        logger.info(f"POST remove -> done")
        return result

    def get_list_member(self, list_id: str) -> list[dict]:
        logger.info(f"GET list member -> start")
        result = []
        ope = {"listId": str}, Operation.ListMembers[0], Operation.ListMembers[1]
        response = self.scraper._run(ope, [str(list_id)])
        result = find_values(response, "user_results")
        logger.info(f"GET list member -> done")
        return result

    def add_list_member(self, list_id: str, screen_name: str) -> dict:
        logger.info(f"POST list member, target user is '{screen_name}' -> start")
        target_user = self.lookup_user_by_screen_name(screen_name)
        target_id = int(find_values(target_user, "rest_id")[0])
        response = self.account.add_list_member(int(list_id), int(target_id))
        result = find_values(response, "user_results")[0]
        logger.info(f"POST list member, target user is '{screen_name}' -> done")
        return result

    def remove_list_member(self, list_id: str, screen_name: str) -> dict:
        logger.info(f"POST list member, target user is '{screen_name}' -> start")
        target_user = self.lookup_user_by_screen_name(screen_name)
        target_id = int(find_values(target_user, "rest_id")[0])
        response = self.account.remove_list_member(int(list_id), int(target_id))
        result = find_values(response, "user_results")[0]
        logger.info(f"POST list member, target user is '{screen_name}' -> done")
        return result

    def get_mute_keyword_list(self) -> dict:
        logger.info("Getting mute word list all -> start")
        path = "mutes/keywords/list.json"
        params = {}
        headers = get_headers(self.account.session)
        r: Response = self.account.session.get(f"{self.account.v1_api}/{path}", headers=headers, params=params)
        result: dict = r.json()
        logger.info("Getting mute word list all -> done")
        return result

    def mute_keyword(self, keyword: str) -> dict:
        logger.info(f"POST mute word mute, target is '{keyword}' -> start")
        path = "mutes/keywords/create.json"
        payload = {
            "keyword": keyword,
            "mute_surfaces": "notifications,home_timeline,tweet_replies",
            "mute_option": "",
            "duration": "",
        }
        result = self.account.v1(path, payload)
        logger.info(f"POST mute word mute, target is '{keyword}' -> done")
        return result

    def unmute_keyword(self, keyword: str) -> dict:
        logger.info(f"POST muted word unmute, target is '{keyword}' -> start")

        r_dict: dict = self.get_mute_keyword_list()
        target_keyword_dict_list: list[dict] = [d for d in r_dict.get("muted_keywords") if d.get("keyword") == keyword]
        if not target_keyword_dict_list:
            raise ValueError("Target muted word is not found.")
        elif len(target_keyword_dict_list) != 1:
            raise ValueError("Target muted word is multiple found.")
        target_keyword_dict = target_keyword_dict_list[0]
        unmute_keyword_id = target_keyword_dict.get("id")

        path = "mutes/keywords/destroy.json"
        payload = {
            "ids": unmute_keyword_id,
        }
        result = self.account.v1(path, payload)
        logger.info(f"POST muted word unmute, target is '{keyword}' -> done")
        return result

    def mute_user(self, screen_name: str) -> dict:
        logger.info(f"POST mute user mute, target is '{screen_name}' -> start")
        path = "mutes/users/create.json"
        payload = {
            "screen_name": screen_name,
        }
        result = self.account.v1(path, payload)
        logger.info(f"POST mute user mute, target is '{screen_name}' -> done")
        return result

    def unmute_user(self, screen_name: str) -> dict:
        logger.info(f"POST muted user unmute, target is '{screen_name}' -> start")
        path = "mutes/users/destroy.json"
        payload = {
            "screen_name": screen_name,
        }
        result = self.account.v1(path, payload)
        logger.info(f"POST muted user unmute, target is '{screen_name}' -> done")
        return result


if __name__ == "__main__":
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)

    import configparser

    config = configparser.ConfigParser()
    CONFIG_FILE_NAME = "./config/config.ini"
    if not config.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    ct0 = config["twitter_api_client"]["ct0"]
    auth_token = config["twitter_api_client"]["auth_token"]
    target_screen_name = config["twitter_api_client"]["target_screen_name"]
    twitter = TwitterAPI(ct0, auth_token, target_screen_name)
    result: dict | list[dict] = []

    def save_response(result_data):
        RESPONSE_CACHE_PATH = "./response.txt"
        with Path(RESPONSE_CACHE_PATH).open("w") as fout:
            json.dump(result_data, fout, indent=4)

    # pprint.pprint("user 情報取得")
    # screen_name = twitter.target_screen_name
    # result = twitter.lookup_user_by_screen_name(screen_name)
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("user me 情報取得")
    # result = twitter.lookup_me()
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("like 取得")
    # result = twitter.get_likes(twitter.target_screen_name, 10)
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("TL 取得")
    # result = twitter.get_user_timeline(twitter.target_screen_name, 30)
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("ツイート投稿")
    # result = twitter.post_tweet("test")
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("ツイート詳細取得")
    # tweet_id = twitter._find_values(result, "rest_id")[0]
    # result = twitter.lookup_tweet(tweet_id)
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("ツイート削除")
    # result = twitter.delete_tweet(tweet_id)
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("following 取得")
    # result = twitter.get_following_list()
    # save_response(result)
    # pprint.pprint(len(result))
    # for user_dict in result:
    #     legacy = user_dict.get("result", {}).get("legacy", {})
    #     user_id = user_dict.get("result", {}).get("rest_id", "")
    #     user_name = legacy.get("name", "")
    #     screen_name = legacy.get("screen_name", "")
    #     pprint.pprint(f"{user_id}, {user_name}, {screen_name}")

    # pprint.pprint("follower 取得")
    # result = twitter.get_follower_list()
    # save_response(result)
    # pprint.pprint(len(result))
    # for user_dict in result:
    #     legacy = user_dict.get("result", {}).get("legacy", {})
    #     user_id = user_dict.get("result", {}).get("rest_id", "")
    #     user_name = legacy.get("name", "")
    #     screen_name = legacy.get("screen_name", "")
    #     pprint.pprint(f"{user_id}, {user_name}, {screen_name}")

    pprint.pprint("ユーザー follow")
    user = twitter.lookup_user_by_screen_name("X")
    user_id = twitter.find_values(user, "rest_id")[0]
    result = twitter.follow(user_id)
    save_response(result)
    pprint.pprint(len(result))

    pprint.pprint("ユーザー unfollow")
    user = twitter.lookup_user_by_screen_name("X")
    user_id = twitter.find_values(user, "rest_id")[0]
    result = twitter.remove(user_id)
    save_response(result)
    pprint.pprint(len(result))

    # pprint.pprint("list メンバー取得")
    # list_id = "1618833354572595200"  # v_shift9738 - following
    # # list_id = "1673887391667593216"
    # result = twitter.get_list_member(list_id)
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("list メンバー追加")
    # list_id = "1618833354572595200"  # v_shift9738 - following
    # screen_name = ""
    # result = twitter.add_list_member(list_id, screen_name)
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("ミュートワードリスト取得")
    # result = twitter.get_mute_keyword_list()
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("ミュートワード追加")
    # keyword = "test"
    # result = twitter.mute_keyword(keyword)
    # save_response(result)
    # pprint.pprint(len(result))

    # sleep(5)

    # pprint.pprint("ミュートワード解除")
    # keyword = "test"
    # result = twitter.unmute_keyword(keyword)
    # save_response(result)
    # pprint.pprint(len(result))

    # pprint.pprint("ミュートユーザー追加")
    # authorize_screen_name = "o_shift4607"
    # result = twitter.mute_user(authorize_screen_name)
    # save_response(result)
    # pprint.pprint(len(result))

    # sleep(5)

    # pprint.pprint("ミュートユーザー解除")
    # authorize_screen_name = "o_shift4607"
    # result = twitter.unmute_user(authorize_screen_name)
    # save_response(result)
    # pprint.pprint(len(result))

    pass
