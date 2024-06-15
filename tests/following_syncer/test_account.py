import sys
import unittest
from collections import namedtuple
from pathlib import Path

import orjson
from mock import patch

from following_syncer.account import Account
from following_syncer.util import AccountType


class TestAccount(unittest.TestCase):
    def setUp(self) -> None:
        Account.CACHE_PATH = Path("./tests/following_syncer/cache")
        return super().setUp()

    def tearDown(self) -> None:
        cache_path = Path("./tests/following_syncer/cache")
        Path(cache_path / "dummy_screen_name_following.json").unlink(missing_ok=True)
        Path(cache_path / "dummy_screen_name_dummy_list_id_list.json").unlink(missing_ok=True)
        return super().tearDown()

    def _get_config_dict(self) -> dict:
        return {
            "master": {
                "account": {
                    "ct0": "dummy_ct0",
                    "auth_token": "dummy_auth_token",
                    "screen_name": "dummy_screen_name",
                    "list_id": "dummy_list_id",
                    "diff_solve_each_num": 10,
                },
                "list": {"to_be_add": [], "to_be_removed": []},
            },
            "slave": {
                "account_list": [
                    {
                        "account": {
                            "ct0": "dummy_ct0",
                            "auth_token": "dummy_auth_token",
                            "screen_name": "dummy_screen_name",
                            "list_id": "dummy_list_id",
                            "diff_solve_each_num": 10,
                        },
                        "following": {"to_be_add": [], "to_be_removed": []},
                        "list": {"to_be_add": [], "to_be_removed": []},
                    },
                ]
            },
        }

    def _get_entry_list(self, num: int = 5) -> dict:
        entry_list = [
            {
                "result": {
                    "rest_id": f"dummy_rest_id_{index + 1}",
                    "legacy": {
                        "name": f"dummy_name_{index + 1}",
                        "screen_name": f"dummy_screen_name_{index + 1}",
                        "protected": False,
                    },
                }
            }
            for index in range(num)
        ]
        return entry_list

    def test_init(self):
        mock_twitter_api = self.enterContext(patch("following_syncer.account.TwitterAPI"))
        account_config_dict = self._get_config_dict()
        cache_path = Path("./tests/following_syncer/cache")
        following_cache_path = Path(cache_path / "dummy_screen_name_following.json")
        list_cache_path = Path(cache_path / "dummy_screen_name_dummy_list_id_list.json")

        Params = namedtuple("Params", ["account_config_dict", "account_type", "is_dry_run"])

        def pre_run(params: Params) -> None:
            mock_twitter_api.reset_mock()
            entry_list = self._get_entry_list()
            if params.is_dry_run:
                following_cache_path.write_bytes(orjson.dumps(entry_list, orjson.OPT_INDENT_2))
                list_cache_path.write_bytes(orjson.dumps(entry_list, orjson.OPT_INDENT_2))
            else:
                following_cache_path.unlink(missing_ok=True)
                list_cache_path.unlink(missing_ok=True)
                mock_twitter_api.return_value.get_following_list.side_effect = lambda: entry_list
                mock_twitter_api.return_value.get_list_member.side_effect = lambda list_id: entry_list

        def post_run(params: Params, instance: Account) -> None:
            config = params.account_config_dict["account"]
            screen_name = config["screen_name"]
            mock_twitter_api.assert_called_once_with(config["ct0"], config["auth_token"], screen_name)

            self.assertEqual(screen_name, instance.screen_name)
            self.assertEqual(mock_twitter_api.return_value, instance.twitter)
            self.assertEqual(mock_twitter_api.return_value.target_id, instance.user_id)
            self.assertEqual(config["list_id"], instance.list_id)
            self.assertEqual(int(config["diff_solve_each_num"]), instance.diff_solve_each_num)
            self.assertEqual(params.account_type, instance.account_type)
            self.assertEqual(params.is_dry_run, instance.is_dry_run)
            if params.is_dry_run:
                pass
            else:
                self.assertTrue(following_cache_path.exists())
                self.assertTrue(list_cache_path.exists())

        params_list = [
            Params(account_config_dict["master"], AccountType.master, True),
            Params(account_config_dict["slave"]["account_list"][0], AccountType.slave, True),
            Params(account_config_dict["master"], AccountType.master, False),
            Params(account_config_dict["slave"]["account_list"][0], AccountType.slave, False),
        ]
        for params in params_list:
            pre_run(params)
            instance = Account(params.account_config_dict, params.account_type, params.is_dry_run)
            post_run(params, instance)

    def test_create(self):
        mock_twitter_api = self.enterContext(patch("following_syncer.account.TwitterAPI"))
        account_config_dict = self._get_config_dict()
        cache_path = Path("./tests/following_syncer/cache")
        following_cache_path = Path(cache_path / "dummy_screen_name_following.json")
        list_cache_path = Path(cache_path / "dummy_screen_name_dummy_list_id_list.json")
        entry_list = self._get_entry_list()
        following_cache_path.write_bytes(orjson.dumps(entry_list, orjson.OPT_INDENT_2))
        list_cache_path.write_bytes(orjson.dumps(entry_list, orjson.OPT_INDENT_2))

        expect = Account(account_config_dict["master"], AccountType.master, True)
        actual = Account.create(account_config_dict["master"], AccountType.master, True)
        self.assertEqual(expect.screen_name, actual.screen_name)
        self.assertEqual(expect.twitter, actual.twitter)
        self.assertEqual(expect.user_id, actual.user_id)
        self.assertEqual(expect.list_id, actual.list_id)
        self.assertEqual(expect.diff_solve_each_num, actual.diff_solve_each_num)
        self.assertEqual(expect.account_type, actual.account_type)
        self.assertEqual(expect.is_dry_run, actual.is_dry_run)
        self.assertEqual(expect.following_user, actual.following_user)
        self.assertEqual(expect.list_user, actual.list_user)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
