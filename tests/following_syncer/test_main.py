import sys
import unittest
from collections import namedtuple
from pathlib import Path

import orjson
from mock import MagicMock, call, patch

from following_syncer.main import FollowingSyncer
from following_syncer.user import FollowingUser, ListUser, User
from following_syncer.util import AccountType, Result


class TestFollowingSyncer(unittest.TestCase):
    def setUp(self) -> None:
        mock_logger = self.enterContext(patch("following_syncer.main.logger"))
        self.cache_path = Path("./tests/following_syncer/cache/following_syncer_config.json")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        return super().setUp()

    def tearDown(self) -> None:
        self.cache_path.unlink(missing_ok=True)
        return super().tearDown()

    def _get_instance(self) -> FollowingSyncer:
        self.mock_load_master = self.enterContext(patch("following_syncer.main.FollowingSyncer._load_master"))
        self.mock_load_slave_list = self.enterContext(patch("following_syncer.main.FollowingSyncer._load_slave_list"))
        mock_argparse = self._return_argparse()
        self.mock_load_master.return_value = self._return_load_master()
        self.mock_load_slave_list.return_value = self._return_load_slave_list()

        config_json_path = Path("./tests/config/dummy_following_syncer_config.json")
        instance = FollowingSyncer(config_json_path, mock_argparse)
        instance.config_json_path = self.cache_path
        return instance

    def _return_argparse(self) -> MagicMock:
        mock_argparse = MagicMock()
        mock_args = MagicMock()
        mock_args.dry_run = False
        mock_argparse.parse_args.side_effect = lambda: mock_args
        return mock_argparse

    def _return_load_master(self) -> MagicMock:
        r = MagicMock()
        r.screen_name = "master_screen_name"
        r.user_id = 0
        r.list_id = "master_list_id"
        r.diff_solve_each_num = 10
        r.account_type = AccountType.master
        r.is_dry_run = False
        r.following_user = [FollowingUser.create(self._get_user(index)) for index in range(1, 5 + 1)]
        r.list_user = [ListUser.create(self._get_user(index)) for index in range(1, 3 + 1)]
        return r

    def _return_load_slave_list(self) -> list[MagicMock]:
        slave_list = []
        for index in range(2):
            r = MagicMock()
            r.screen_name = f"slave_screen_name_{index}"
            r.user_id = 0
            r.list_id = f"master_list_id_{index}"
            r.diff_solve_each_num = 10
            r.account_type = AccountType.slave
            r.is_dry_run = False
            r.following_user = [FollowingUser.create(self._get_user(index)) for index in range(1, 5 + 1)]
            r.list_user = [ListUser.create(self._get_user(index)) for index in range(1, 3 + 1)]
            slave_list.append(r)
        return slave_list

    def _get_user(self, index: int, protected: bool = False) -> User:
        return User(f"{index}", f"test_user🎉_{index}", f"test_user_{index}", protected)

    def test_init(self):
        mock_load_master = self.enterContext(patch("following_syncer.main.FollowingSyncer._load_master"))
        mock_load_slave_list = self.enterContext(patch("following_syncer.main.FollowingSyncer._load_slave_list"))
        mock_argparse = self._return_argparse()
        config_json_path = Path("./tests/config/dummy_following_syncer_config.json")
        config_dict = orjson.loads(config_json_path.read_bytes())

        instance = FollowingSyncer(config_json_path, mock_argparse)
        mock_argparse.parse_args.assert_called_once_with()
        mock_load_master.assert_called_once_with()
        mock_load_slave_list.assert_called_once_with()
        self.assertEqual(config_json_path, instance.config_json_path)
        self.assertEqual(config_dict, instance.config_dict)
        self.assertEqual(mock_load_master.return_value, instance.master)
        self.assertEqual(mock_load_slave_list.return_value, instance.slave_list)
        self.assertFalse(instance.is_dry_run)

    def test_load_master(self):
        mock_account = self.enterContext(patch("following_syncer.main.Account"))
        mock_load_slave_list = self.enterContext(patch("following_syncer.main.FollowingSyncer._load_slave_list"))
        mock_argparse = self._return_argparse()
        config_json_path = Path("./tests/config/dummy_following_syncer_config.json")
        config_dict = orjson.loads(config_json_path.read_bytes())

        instance = FollowingSyncer(config_json_path, mock_argparse)
        mock_account.create.assert_called_once_with(config_dict["master"], AccountType.master, instance.is_dry_run)
        self.assertEqual(mock_account.create.return_value, instance.master)
        mock_load_slave_list.assert_called_once_with()

    def test_load_slave_list(self):
        mock_account = self.enterContext(patch("following_syncer.main.Account"))
        mock_load_master = self.enterContext(patch("following_syncer.main.FollowingSyncer._load_master"))
        mock_argparse = self._return_argparse()
        config_json_path = Path("./tests/config/dummy_following_syncer_config.json")
        config_dict = orjson.loads(config_json_path.read_bytes())
        slave_account_dict = config_dict["slave"]["account_list"]

        instance = FollowingSyncer(config_json_path, mock_argparse)
        self.assertEqual(
            [call.create(account_dict, AccountType.slave, instance.is_dry_run) for account_dict in slave_account_dict],
            mock_account.mock_calls,
        )
        self.assertEqual([mock_account.create.return_value for _ in slave_account_dict], instance.slave_list)
        mock_load_master.assert_called_once_with()

    def test_deff_account(self):
        instance = self._get_instance()
        p = [self._get_user(index) for index in [0, 1]]
        q = [self._get_user(index) for index in [0, 2]]
        actual = instance._deff_account(p, q)
        self.assertEqual(([self._get_user(1)], [self._get_user(2)]), actual)

        p = [self._get_user(index) for index in [0, 1, 1]]
        q = [self._get_user(index) for index in [0, 2, 2]]
        actual = instance._deff_account(p, q)
        self.assertEqual(([self._get_user(1)], [self._get_user(2)]), actual)

    def test_exclude_account(self):
        instance = self._get_instance()
        user_list = [User("0", "master_name", "master_screen_name", False)]
        user_list.extend([
            User(str(index + 1), f"slave_name_{index}", f"slave_screen_name_{index}", False) for index in range(2)
        ])
        user_list.extend([
            User(str(index + 1 + 2), f"protected_name_{index}", f"protected_screen_name_{index}", True)
            for index in range(5)
        ])
        user_list.extend([
            User(str(index + 1 + 2 + 5), f"leave_name_{index}", f"leave_screen_name_{index}", False)
            for index in range(5)
        ])
        expect = user_list[-5:]
        actual = instance._exclude_account(user_list)
        self.assertEqual(expect, actual)

        actual = instance._exclude_account(user_list[-1:])
        self.assertEqual(user_list[-1:], actual)

        actual = instance._exclude_account([])
        self.assertEqual([], actual)

        actual = instance._exclude_account(["invalid_argument"])
        self.assertEqual([], actual)

        actual = instance._exclude_account(user_list[-1])
        self.assertEqual([], actual)

        actual = instance._exclude_account("invalid_argument")
        self.assertEqual([], actual)

    def test_master_sync(self):
        Params = namedtuple("Params", ["is_skip", "is_dry_run", "is_add_error", "is_remove_error"])

        def pre_run(params: Params, instance: FollowingSyncer) -> FollowingSyncer:
            mock_twitter = MagicMock()
            instance.master.twitter = mock_twitter
            if params.is_skip:
                instance.master.following_user = []
                instance.master.list_user = []
            else:
                instance.master.following_user = [
                    FollowingUser.create(self._get_user(index)) for index in [1, 2, 3, 4, 5]
                ]
                instance.master.list_user = [ListUser.create(self._get_user(index)) for index in [3, 4, 5, 6, 7]]
            instance.is_dry_run = params.is_dry_run
            if not params.is_dry_run:
                if params.is_add_error:
                    mock_twitter.add_list_member.side_effect = ValueError
                if params.is_remove_error:
                    mock_twitter.remove_list_member.side_effect = ValueError
            return instance

        def post_run(params: Params, instance: FollowingSyncer) -> None:
            mock_twitter: MagicMock = instance.master.twitter
            list_id = instance.master.list_id
            if params.is_skip or params.is_dry_run:
                mock_twitter.add_list_member.assert_not_called()
                mock_twitter.remove_list_member.assert_not_called()
            else:
                self.assertEqual(
                    [
                        call.add_list_member(list_id, "test_user_1"),
                        call.add_list_member(list_id, "test_user_2"),
                        call.remove_list_member(list_id, "test_user_6"),
                        call.remove_list_member(list_id, "test_user_7"),
                    ],
                    mock_twitter.mock_calls,
                )

        params_list = [
            Params(False, False, False, False),
            Params(True, False, False, False),
            Params(False, True, False, False),
            Params(False, False, True, False),
            Params(False, False, False, True),
        ]
        for params in params_list:
            instance = self._get_instance()
            instance = pre_run(params, instance)
            actual = instance.master_sync()
            self.assertEqual(Result.success, actual)
            post_run(params, instance)

    def test_following_sync(self):
        Params = namedtuple("Params", ["is_skip", "is_dry_run", "is_add_error", "is_remove_error"])

        def pre_run(params: Params, instance: FollowingSyncer) -> FollowingSyncer:
            mock_twitter = MagicMock()
            if params.is_skip:
                instance.master.following_user = []

                r = MagicMock()
                r.screen_name = f"slave_screen_name_0"
                r.user_id = 0
                r.list_id = f"master_list_id_0"
                r.diff_solve_each_num = 10
                r.account_type = AccountType.slave
                r.is_dry_run = False
                r.following_user = []
                r.list_user = []
                instance.slave_list = [r]
            else:
                instance.master.following_user = [
                    FollowingUser.create(self._get_user(index)) for index in [1, 2, 3, 4, 5]
                ]

                r = MagicMock()
                r.screen_name = f"slave_screen_name_0"
                r.user_id = 0
                r.list_id = f"master_list_id_0"
                r.diff_solve_each_num = 10
                r.account_type = AccountType.slave
                r.is_dry_run = False
                r.following_user = [FollowingUser.create(self._get_user(index)) for index in [3, 4, 5, 6, 7]]
                r.list_user = [ListUser.create(self._get_user(index)) for index in [3, 4, 5, 6, 7]]
                r.twitter = mock_twitter
                instance.slave_list = [r]
            instance.is_dry_run = params.is_dry_run
            if not params.is_dry_run:
                if params.is_add_error:
                    mock_twitter.follow.side_effect = ValueError
                if params.is_remove_error:
                    mock_twitter.remove.side_effect = ValueError
            return instance

        def post_run(params: Params, instance: FollowingSyncer) -> None:
            mock_twitter: MagicMock = instance.slave_list[0].twitter
            if params.is_skip or params.is_dry_run:
                mock_twitter.follow.assert_not_called()
                mock_twitter.remove.assert_not_called()
            else:
                self.assertEqual(
                    [
                        call.follow("1"),
                        call.follow("2"),
                        call.remove("6"),
                        call.remove("7"),
                    ],
                    mock_twitter.mock_calls,
                )

        params_list = [
            Params(False, False, False, False),
            Params(True, False, False, False),
            Params(False, True, False, False),
            Params(False, False, True, False),
            Params(False, False, False, True),
        ]
        for params in params_list:
            instance = self._get_instance()
            instance = pre_run(params, instance)
            actual = instance.following_sync()
            self.assertEqual(Result.success, actual)
            post_run(params, instance)

    def test_list_sync(self):
        Params = namedtuple("Params", ["is_skip", "is_dry_run", "is_add_error", "is_remove_error"])

        def pre_run(params: Params, instance: FollowingSyncer) -> FollowingSyncer:
            mock_twitter = MagicMock()
            if params.is_skip:
                instance.master.list_user = []

                r = MagicMock()
                r.screen_name = f"slave_screen_name_0"
                r.user_id = 0
                r.list_id = f"master_list_id_0"
                r.diff_solve_each_num = 10
                r.account_type = AccountType.slave
                r.is_dry_run = False
                r.following_user = []
                r.list_user = []
                instance.slave_list = [r]
            else:
                instance.master.list_user = [ListUser.create(self._get_user(index)) for index in [1, 2, 3, 4, 5]]

                r = MagicMock()
                r.screen_name = f"slave_screen_name_0"
                r.user_id = 0
                r.list_id = f"master_list_id_0"
                r.diff_solve_each_num = 10
                r.account_type = AccountType.slave
                r.is_dry_run = False
                r.following_user = [FollowingUser.create(self._get_user(index)) for index in [3, 4, 5, 6, 7]]
                r.list_user = [ListUser.create(self._get_user(index)) for index in [3, 4, 5, 6, 7]]
                r.twitter = mock_twitter
                instance.slave_list = [r]
            instance.is_dry_run = params.is_dry_run
            if not params.is_dry_run:
                if params.is_add_error:
                    mock_twitter.add_list_member.side_effect = ValueError
                if params.is_remove_error:
                    mock_twitter.remove_list_member.side_effect = ValueError
            return instance

        def post_run(params: Params, instance: FollowingSyncer) -> None:
            mock_twitter: MagicMock = instance.slave_list[0].twitter
            list_id = instance.slave_list[0].list_id
            if params.is_skip or params.is_dry_run:
                mock_twitter.add_list_member.assert_not_called()
                mock_twitter.remove_list_member.assert_not_called()
            else:
                self.assertEqual(
                    [
                        call.add_list_member(list_id, "test_user_1"),
                        call.add_list_member(list_id, "test_user_2"),
                        call.remove_list_member(list_id, "test_user_6"),
                        call.remove_list_member(list_id, "test_user_7"),
                    ],
                    mock_twitter.mock_calls,
                )

        params_list = [
            Params(False, False, False, False),
            Params(True, False, False, False),
            Params(False, True, False, False),
            Params(False, False, True, False),
            Params(False, False, False, True),
        ]
        for params in params_list:
            instance = self._get_instance()
            instance = pre_run(params, instance)
            actual = instance.list_sync()
            self.assertEqual(Result.success, actual)
            post_run(params, instance)

    def test_sync(self):
        mock_master_sync = self.enterContext(patch("following_syncer.main.FollowingSyncer.master_sync"))
        mock_following_sync = self.enterContext(patch("following_syncer.main.FollowingSyncer.following_sync"))
        mocklist_sync = self.enterContext(patch("following_syncer.main.FollowingSyncer.list_sync"))
        instance = self._get_instance()
        actual = instance.sync()
        self.assertEqual(Result.success, actual)
        mock_master_sync.assert_called_once_with()
        mock_following_sync.assert_called_once_with()
        mocklist_sync.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
