# coding: utf-8
import configparser
import datetime
import json
import os
import pprint
import re
from copy import deepcopy
from enum import Enum
from pathlib import Path

from requests_oauthlib import OAuth1Session

FILE_NAME_BASE = "ff_list"
os.chdir(os.path.dirname(__file__))

config = configparser.ConfigParser()
config.read_file(Path("config.ini").open("r", encoding="utf-8"))

API_KEY = config["twitter_token_keys_v2"]["api_key"]
API_KEY_SECRET = config["twitter_token_keys_v2"]["api_key_secret"]
ACCESS_TOKEN_KEY = config["twitter_token_keys_v2"]["access_token"]
ACCESS_TOKEN_SECRET = config["twitter_token_keys_v2"]["access_token_secret"]

oauth = OAuth1Session(
    API_KEY,
    API_KEY_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET
)


class TwitterAPIEndpoint(Enum):
    USER_LOOKUP_ME = "https://api.twitter.com/2/users/me"
    FOLLOWING = "https://api.twitter.com/2/users/{}/following"
    FOLLOWERS = "https://api.twitter.com/2/users/{}/followers"
    POST_TWEET = "https://api.twitter.com/2/tweets"


def get_last_file_path() -> Path | None:
    """前回実行ファイルのパスを取得する

    Returns:
        last_file_path (Path | None): 前回実行ファイルのパス, 存在しない場合None
    """
    last_file_path: Path

    # カレントディレクトリから FILE_NAME_BASE をファイル名に持つすべてのファイルパスを取得
    prev_file_path_list = list(Path().glob(f"{FILE_NAME_BASE}*"))
    if not prev_file_path_list:
        # 前回実行ファイルが無かった = 初回実行
        return None

    # 前回実行のうち最新のパスを保持
    last_file_path = prev_file_path_list[-1]
    today_datetime = datetime.date.today()
    today_str = today_datetime.strftime("%Y%m%d")
    if today_str in last_file_path.name:
        # 今日と同じ日付がファイル名に含まれる = 初回実行ではないが実行済
        if len(prev_file_path_list) > 1:
            # 2つ以上見つかっているならば
            # 前回ファイルを2つ前のファイルとする = 今日でなく、その前に実行したときのファイル
            last_file_path = prev_file_path_list[-2]
        else:
            # 本日実行分しかなかったため、前回実行分は無かった
            return None

    return last_file_path


def get_diff(following_list: list[dict], follower_list: list[dict]) -> tuple[list[dict], list[dict]]:
    """前回実行ファイルと比較してdiffを得る

    Args:
        following_list (list[dict]): 今回実行の following
        follower_list (list[dict]): 今回実行の follower

    Returns:
        diff_following_list (list[dict]): 今回実行と前回実行の following の diff
        diff_follower_list (list[dict]): 今回実行と前回実行の follower の diff
    """
    last_file_path = get_last_file_path()
    if not last_file_path:
        return [], []

    # 前回実行ファイルを読み込む
    pattern = "^(.*?), (.*), (.*?)$"
    now_kind = "following"
    prev_following_list = []
    prev_follower_list = []
    with last_file_path.open("r", encoding="utf-8") as fin:
        for line in fin:
            if re.findall("^difference(.*)", line):
                # difference の文言があるブロックまで来たら読み込み終了
                break
            if re.findall("^follower$", line):
                # follower の文言があるブロックまで来たらこれ以降は follower
                now_kind = "follower"
            if records := re.findall(pattern, line):
                record = records[0]
                if record[0] == "id":
                    continue
                r = {
                    "id": record[0],
                    "name": record[1],
                    "username": record[2],
                }
                if now_kind == "following":
                    prev_following_list.append(r)
                elif now_kind == "follower":
                    prev_follower_list.append(r)
                else:
                    raise ValueError("prev file format error.")

    def list_diff(p_list, q_list):
        p_list = deepcopy(p_list)
        q_list = deepcopy(q_list)

        # 順序保持用の order_id を付与
        for i, p in enumerate(p_list):
            p["order_id"] = i
        for i, q in enumerate(q_list):
            q["order_id"] = i + len(p_list) + 1

        p = [r["id"] for r in p_list]
        q = [r["id"] for r in q_list]

        result = []
        # 集合演算：排他的論理和
        diff_list = set(p) ^ set(q)
        for diff_id in diff_list:
            if diff_id in p:
                record = [r for r in p_list if r["id"] == diff_id][0]
                record["diff_type"] = "ADD"
                result.append(record)
            elif diff_id in q:
                record = [r for r in q_list if r["id"] == diff_id][0]
                record["diff_type"] = "REMOVE"
                result.append(record)
        result.sort(key=lambda r: r["order_id"])
        return result

    diff_following_list = list_diff(following_list, prev_following_list)
    diff_follower_list = list_diff(follower_list, prev_follower_list)
    return diff_following_list, diff_follower_list


def post_tweet(tweet_str: str) -> dict:
    """実行完了ツイートをポストする

    Args:
        tweet_str (str): ポストする文字列

    Returns:
        response (dict): post後のレスポンス
    """
    url = TwitterAPIEndpoint.POST_TWEET.value

    params = {
        "text": tweet_str,
    }

    response = oauth.post(url, json=params)
    response.raise_for_status()

    return json.loads(response.text)


def main():
    # ユーザID取得
    url = TwitterAPIEndpoint.USER_LOOKUP_ME.value
    res = oauth.get(url, params={})
    res.raise_for_status()
    user_data = json.loads(res.text)

    user_id = user_data.get("data", {}).get("id", "")
    if not user_id:
        msg = pprint.pformat(user_data)
        raise ValueError(f"user_id getting failed : \n{msg}")

    # フォローしているユーザを取得
    MAX_RESULTS = 1000
    url = TwitterAPIEndpoint.FOLLOWING.value.format(user_id)
    next_token = ""
    following_list = []
    while True:
        params = {
            "max_results": MAX_RESULTS
        }
        if next_token != "":
            params["pagination_token"] = next_token
        res = oauth.get(url, params=params)
        res.raise_for_status()
        data_dict = json.loads(res.text)

        data_list = data_dict.get("data", [])
        following_list.extend(data_list)

        next_token = data_dict.get("meta", {}).get("next_token", "")
        if next_token == "":
            break
    # pprint.pprint(following_list)

    # フォローされているユーザを取得
    url = TwitterAPIEndpoint.FOLLOWERS.value.format(user_id)
    next_token = ""
    follower_list = []
    while True:
        params = {
            "max_results": MAX_RESULTS
        }
        if next_token != "":
            params["pagination_token"] = next_token
        res = oauth.get(url, params=params)
        res.raise_for_status()
        data_dict = json.loads(res.text)

        data_list = data_dict.get("data", [])
        follower_list.extend(data_list)

        next_token = data_dict.get("meta", {}).get("next_token", "")
        if next_token == "":
            break
    # pprint.pprint(follower_list)

    # 前回実行からの差分を取得
    last_file_path = get_last_file_path()
    diff_following_list, diff_follower_list = get_diff(following_list, follower_list)

    # ファイルに保存
    today_datetime = datetime.date.today()
    today_str = today_datetime.strftime("%Y%m%d")
    with Path(f"{FILE_NAME_BASE}_{today_str}.txt").open("w", encoding="utf-8") as fout:
        # フォローしているユーザ
        # id, name, screen_name
        fout.write(f"{today_str}\n")
        fout.write("following\n")
        fout.write("id, name, screen_name\n")
        for following_data in following_list:
            data_line = "{}, {}, {}\n".format(
                following_data.get("id"),
                following_data.get("name"),
                following_data.get("username"),
            )
            fout.write(data_line)

        # フォローされているユーザ
        # id, name, screen_name
        fout.write("\n")
        fout.write("follower\n")
        fout.write("id, name, screen_name\n")
        for follower_data in follower_list:
            data_line = "{}, {}, {}\n".format(
                follower_data.get("id"),
                follower_data.get("name"),
                follower_data.get("username"),
            )
            fout.write(data_line)

        # 前回実行ファイルが存在するならば
        if last_file_path:
            # フォローしているユーザの差分
            # diff_type, id, name, screen_name
            fout.write("\n")
            fout.write(f"difference with {last_file_path.name}\n")
            fout.write("following\n")
            fout.write("diff_type, id, name, screen_name\n")
            for following_data in diff_following_list:
                data_line = "{}, {}, {}, {}\n".format(
                    following_data.get("diff_type"),
                    following_data.get("id"),
                    following_data.get("name"),
                    following_data.get("username"),
                )
                fout.write(data_line)

            # フォローされているユーザの差分
            # diff_type, id, name, screen_name
            fout.write("\n")
            fout.write("follower\n")
            fout.write("diff_type, id, name, screen_name\n")
            for follower_data in diff_follower_list:
                data_line = "{}, {}, {}, {}\n".format(
                    follower_data.get("diff_type"),
                    follower_data.get("id"),
                    follower_data.get("name"),
                    follower_data.get("username"),
                )
                fout.write(data_line)

    # コンソール表示
    print(f"following num : {len(following_list)}")
    print(f"follower num : {len(follower_list)}")
    print("following : ")
    pprint.pprint(following_list)
    print("")
    print("follower : ")
    pprint.pprint(follower_list)
    if last_file_path:
        print("")
        print(f"difference with {last_file_path.name}")
        print("following : ")
        pprint.pprint(diff_following_list)

        print("")
        print("follower")
        pprint.pprint(diff_follower_list)

    # 完了リプライ通知を送信
    done_msg = "FFGetter run.\n"
    done_msg += datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    done_msg += " Process Done.\n"
    done_msg += f"follow num : {len(following_list)} , "
    done_msg += f"follower num : {len(follower_list)}\n"

    tweet_str = ""
    try:
        reply_user_name = config["notification"]["reply_to_user_name"]
        if reply_user_name == "":
            tweet_str = done_msg
        else:
            tweet_str = "@" + reply_user_name + " " + done_msg
    except Exception:
        tweet_str = done_msg

    print("")
    if post_tweet(tweet_str):
        print("Reply posted.")
    else:
        print("Reply post failed.")


if __name__ == "__main__":
    main()
