from logging import INFO, getLogger
from pathlib import Path
from typing import Self

import orjson

from following_syncer.twitter_api import TwitterAPI
from following_syncer.user import FollowingUser, ListUser
from following_syncer.util import AccountType, find_values

logger = getLogger(__name__)
logger.setLevel(INFO)


class Account:
    screen_name: str
    user_id: int
    list_id: str
    diff_solve_each_num: int
    account_type: AccountType
    is_dry_run: bool
    following_user: list[FollowingUser]
    list_user: list[ListUser]

    CACHE_PATH = Path(__file__).parent / "cache"

    def __init__(
        self,
        account_config_dict: dict,
        account_type: AccountType,
        is_dry_run: bool = True,
    ) -> None:
        config = account_config_dict["account"]
        self.screen_name = config["screen_name"]
        self.twitter = TwitterAPI(config["ct0"], config["auth_token"], self.screen_name)
        self.user_id = self.twitter.target_id
        self.list_id = config["list_id"]
        self.diff_solve_each_num = int(config["diff_solve_each_num"])
        self.account_type = account_type
        self.is_dry_run = is_dry_run

        self.CACHE_PATH.mkdir(parents=True, exist_ok=True)

        # following
        self.following_user = []
        following_dict: list[dict] = []
        if not self.is_dry_run:
            following_dict = self.twitter.get_following_list()
            Path(self.CACHE_PATH / f"{self.screen_name}_following.json").write_bytes(
                orjson.dumps(following_dict, option=orjson.OPT_INDENT_2)
            )
        else:
            following_dict = orjson.loads(Path(self.CACHE_PATH / f"{self.screen_name}_following.json").read_bytes())
        for user_dict in following_dict:
            t_rest_id = find_values(user_dict, "rest_id", True, ["result"], [])
            t_name = find_values(user_dict, "name", True, ["result", "legacy"], [])
            t_screen_name = find_values(user_dict, "screen_name", True, ["result", "legacy"], [])
            t_protected = find_values(user_dict, "protected", False, ["result", "legacy"], [])
            t_protected = False if len(t_protected) != 1 else t_protected[0]
            user = FollowingUser(t_rest_id, t_name, t_screen_name, t_protected)
            self.following_user.append(user)
        self.following_user.reverse()

        # list
        self.list_user = []
        list_dict: list[dict] = []
        if not self.is_dry_run:
            list_dict = self.twitter.get_list_member(self.list_id)
            Path(self.CACHE_PATH / f"{self.screen_name}_{self.list_id}_list.json").write_bytes(
                orjson.dumps(list_dict, option=orjson.OPT_INDENT_2)
            )
        else:
            list_dict = orjson.loads(
                Path(self.CACHE_PATH / f"{self.screen_name}_{self.list_id}_list.json").read_bytes()
            )
        for user_dict in list_dict:
            t_rest_id = find_values(user_dict, "rest_id", True, ["result"], [])
            t_name = find_values(user_dict, "name", True, ["result", "legacy"], [])
            t_screen_name = find_values(user_dict, "screen_name", True, ["result", "legacy"], [])
            t_protected = find_values(user_dict, "protected", False, ["result", "legacy"], [])
            t_protected = False if len(t_protected) != 1 else t_protected[0]
            user = ListUser(t_rest_id, t_name, t_screen_name, t_protected)
            self.list_user.append(user)
        self.list_user.reverse()

    @classmethod
    def create(cls, account_config_dict: dict, account_type: AccountType, is_dry_run: bool = True) -> Self:
        return Account(account_config_dict, account_type, is_dry_run)


if __name__ == "__main__":
    import argparse

    config_json: Path = Path("./config/following_syncer_config.json")
    config_dict = orjson.loads(config_json.read_bytes())

    arg_parser = argparse.ArgumentParser(
        prog="Following Syncer", description="Sync master account with slave account."
    )
    arg_parser.add_argument("--dry-run", action="store_true")

    account = Account(config_dict["master"], AccountType.master, True)
