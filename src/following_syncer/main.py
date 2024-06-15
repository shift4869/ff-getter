import argparse
import logging.config
from logging import INFO, getLogger
from pathlib import Path

import orjson

from following_syncer.account import Account
from following_syncer.user import User
from following_syncer.util import AccountType, Result

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
for name in logging.root.manager.loggerDict:
    if "following_syncer" not in name and "__main__" not in name:
        getLogger(name).disabled = True
    if "following_syncer" in name and "twitter_api" in name:
        getLogger(name).disabled = True
logger = getLogger(__name__)
logger.setLevel(INFO)


class FollowingSyncer:
    config_json_path: Path
    config_dict: dict
    master: Account
    slave_list: list[Account]
    is_dry_run: bool

    CACHE_PATH = Path(__file__).parent / "cache"

    def __init__(self, config_json_path: Path, arg_parser: argparse.ArgumentParser) -> None:
        """syncer初期化

        Args:
            config_json_path (Path): config ファイルのパス
            arg_parser (argparse.ArgumentParser): 起動時引数のパーサ
        """
        args = arg_parser.parse_args()
        self.is_dry_run = args.dry_run

        self.config_json_path = config_json_path
        self.config_dict = orjson.loads(config_json_path.read_bytes())
        self.master = self._load_master()
        self.slave_list = self._load_slave_list()

    def _load_master(self) -> Account:
        """master のアカウント情報をロードする

        Returns:
            Account: master のアカウント情報
        """
        logger.info("Master account create -> start")
        result = Account.create(self.config_dict["master"], AccountType.master, self.is_dry_run)
        screen_name = self.config_dict["master"]["account"]["screen_name"]
        logger.info(f"\t{screen_name} account created.")
        logger.info("Master account create -> done")
        return result

    def _load_slave_list(self) -> list[Account]:
        """slave のアカウント情報をロードする

        Returns:
            Account: slave のアカウント情報リスト
        """
        logger.info("Slave account create -> start")
        result = []
        slave_account_dict = self.config_dict["slave"]["account_list"]
        for account_dict in slave_account_dict:
            result.append(Account.create(account_dict, AccountType.slave, self.is_dry_run))
            screen_name = account_dict["account"]["screen_name"]
            logger.info(f"\t{screen_name} account created.")
        logger.info(f"Num of slave = {len(result)}")
        logger.info("Slave account create -> done")
        return result

    def _deff_account(self, p: list[User], q: list[User]) -> tuple[list[User], list[User]]:
        """Userリストについて (p - q, q - p) を返す

        rest_id を基準に集合演算を行う

        Args:
            p (list[User]): Userリスト1
            q (list[User]): Userリスト2

        Returns:
            tuple[list[User], list[User]]: p - q, q - p
        """
        p_rest_ids = [r.rest_id for r in p]
        q_rest_ids = [r.rest_id for r in q]
        p_set = set([r for r in p_rest_ids])
        q_set = set([r for r in q_rest_ids])

        all_set = p_set | q_set
        to_be_added = []
        to_be_removed = []
        for ele in all_set:
            if (ele in p_set) and (ele not in q_set):
                # p - q
                user = [r for r in p if r.rest_id == ele]
                if len(user) == 1:
                    to_be_added.append(user[0])
            if (ele not in p_set) and (ele in q_set):
                # q - p
                user = [r for r in q if r.rest_id == ele]
                if len(user) == 1:
                    to_be_removed.append(user[0])
        return to_be_added, to_be_removed

    def _exclude_account(self, user_list: list[User]) -> list[User]:
        """user_list から特定の条件を満たすものを除外する

        Args:
            user_list (list[User]): 操作対象 user_list

        Returns:
            list[User]: 除外後のリスト
        """
        # 今回操作しているアカウント関連は除外
        exclude_screen_names = [self.master.screen_name]
        exclude_screen_names.extend([r.screen_name for r in self.slave_list])
        user_list = [r for r in user_list if r.screen_name not in exclude_screen_names]

        # 鍵アカウントは除外
        user_list = [r for r in user_list if not r.protected]
        return user_list

    def master_sync(self) -> Result:
        """master の following を list に反映させる

        Returns:
            Result: 成功時 Result.success, 失敗時 Result.failed
        """
        logger.info("Run master_sync -> start")
        logger.info(f"Master: {self.master.screen_name} following.")
        logger.info(f"Slave: {self.master.screen_name} list (list_id = '{self.master.list_id}').")
        master_following = self.master.following_user
        master_list = self.master.list_user

        to_be_added_all, to_be_removed_all = self._deff_account(master_following, master_list)
        to_be_added_all = self._exclude_account(to_be_added_all)
        to_be_removed_all = self._exclude_account(to_be_removed_all)
        logger.info(f"After excluded, num of to_be_added_all = {len(to_be_added_all)}")
        logger.info(f"After excluded, num of to_be_removed_all = {len(to_be_removed_all)}")

        if len(to_be_added_all) == 0 and len(to_be_removed_all) == 0:
            logger.info("Synchronization skipped, following/list are already matched.")
            logger.info("Run master_sync -> done")
            return Result.success

        diff_solve_each_num = self.master.diff_solve_each_num
        to_be_added = to_be_added_all[:diff_solve_each_num]
        to_be_added_rest = to_be_added_all[diff_solve_each_num:]
        logger.info(f"Num of to_be_added = {len(to_be_added)}")
        logger.info(f"Num of to_be_added_rest = {len(to_be_added_rest)}")

        to_be_removed = to_be_removed_all[:diff_solve_each_num]
        to_be_removed_rest = to_be_removed_all[diff_solve_each_num:]
        logger.info(f"Num of to_be_removed = {len(to_be_removed)}")
        logger.info(f"Num of to_be_removed_rest = {len(to_be_removed_rest)}")

        list_id = self.master.list_id
        dry_run_log = "dry run " if self.is_dry_run else ""
        logger.info(f"Add to_be_added user -> {dry_run_log}start")
        for user in to_be_added:
            screen_name = user.screen_name
            try:
                if not self.is_dry_run:
                    self.master.twitter.add_list_member(list_id, screen_name)
                logger.info(f"\t{user}")
            except Exception as e:
                logger.error(f"{e}")
        logger.info(f"Add to_be_added user -> {dry_run_log}done")

        logger.info(f"Remove to_be_removed user -> {dry_run_log}start")
        for user in to_be_removed:
            screen_name = user.screen_name
            try:
                if not self.is_dry_run:
                    self.master.twitter.remove_list_member(list_id, screen_name)
                logger.info(f"\t{user}")
            except Exception as e:
                logger.error(f"{e}")
        logger.info(f"Remove to_be_removed user -> {dry_run_log}done")

        logger.info("Update rest -> start")
        self.config_dict["master"]["list"]["to_be_add"] = [r.to_dict() for r in to_be_added_rest]
        self.config_dict["master"]["list"]["to_be_removed"] = [r.to_dict() for r in to_be_removed_rest]
        self.config_json_path.write_bytes(orjson.dumps(self.config_dict, option=orjson.OPT_INDENT_2))
        logger.info("Update rest -> done")
        logger.info("Run master_sync -> done")
        return Result.success

    def following_sync(self) -> Result:
        """master の following を slave の following に反映させる

        Returns:
            Result: 成功時 Result.success, 失敗時 Result.failed
        """
        logger.info("Run following_sync -> start")
        master_following = self.master.following_user
        slave_list = self.slave_list

        dry_run_log = "dry run " if self.is_dry_run else ""
        for i, slave in enumerate(slave_list):
            logger.info(f"Master: {self.master.screen_name} following.")
            logger.info(f"Slave: {slave.screen_name} following.")

            to_be_added_all, to_be_removed_all = self._deff_account(master_following, slave.following_user)
            to_be_added_all = self._exclude_account(to_be_added_all)
            to_be_removed_all = self._exclude_account(to_be_removed_all)
            logger.info(f"After excluded, num of to_be_added_all = {len(to_be_added_all)}")
            logger.info(f"After excluded, num of to_be_removed_all = {len(to_be_removed_all)}")

            if len(to_be_added_all) == 0 and len(to_be_removed_all) == 0:
                logger.info("Synchronization skipped, following/list are already matched.")
                continue

            diff_solve_each_num = slave.diff_solve_each_num
            to_be_added = to_be_added_all[:diff_solve_each_num]
            to_be_added_rest = to_be_added_all[diff_solve_each_num:]
            logger.info(f"Num of to_be_added = {len(to_be_added)}")
            logger.info(f"Num of to_be_added_rest = {len(to_be_added_rest)}")

            to_be_removed = to_be_removed_all[:diff_solve_each_num]
            to_be_removed_rest = to_be_removed_all[diff_solve_each_num:]
            logger.info(f"Num of to_be_removed = {len(to_be_removed)}")
            logger.info(f"Num of to_be_removed_rest = {len(to_be_removed_rest)}")

            logger.info(f"Add to_be_added user -> {dry_run_log}start")
            for user in to_be_added:
                user_id = user.rest_id
                try:
                    if not self.is_dry_run:
                        slave.twitter.follow(user_id)
                    logger.info(f"\t{user}")
                except Exception as e:
                    logger.error(f"{e}")
            logger.info(f"Add to_be_added user -> {dry_run_log}done")

            logger.info(f"Remove to_be_removed user -> {dry_run_log}start")
            for user in to_be_removed:
                user_id = user.rest_id
                try:
                    if not self.is_dry_run:
                        slave.twitter.remove(user_id)
                    logger.info(f"\t{user}")
                except Exception as e:
                    logger.error(f"{e}")

            logger.info(f"Remove to_be_removed user -> {dry_run_log}done")

            self.config_dict["slave"]["account_list"][i]["following"]["to_be_add"] = [
                r.to_dict() for r in to_be_added_rest
            ]
            self.config_dict["slave"]["account_list"][i]["following"]["to_be_removed"] = [
                r.to_dict() for r in to_be_removed_rest
            ]
            logger.info("")

        logger.info("Update rest -> start")
        self.config_json_path.write_bytes(orjson.dumps(self.config_dict, option=orjson.OPT_INDENT_2))
        logger.info("Update rest -> done")
        logger.info("Run following_sync -> done")
        return Result.success

    def list_sync(self) -> Result:
        """master の list を slave の list に反映させる

        Returns:
            Result: 成功時 Result.success, 失敗時 Result.failed
        """
        logger.info("Run list_sync -> start")
        master_list = self.master.list_user
        slave_list = self.slave_list

        dry_run_log = "dry run " if self.is_dry_run else ""
        for i, slave in enumerate(slave_list):
            logger.info(f"Master: {self.master.screen_name} list (list_id = '{self.master.list_id}').")
            logger.info(f"Slave: {slave.screen_name} list (list_id = '{slave.list_id}').")

            to_be_added_all, to_be_removed_all = self._deff_account(master_list, slave.list_user)
            to_be_added_all = self._exclude_account(to_be_added_all)
            to_be_removed_all = self._exclude_account(to_be_removed_all)
            logger.info(f"After excluded, num of to_be_added_all = {len(to_be_added_all)}")
            logger.info(f"After excluded, num of to_be_removed_all = {len(to_be_removed_all)}")

            if len(to_be_added_all) == 0 and len(to_be_removed_all) == 0:
                logger.info("Synchronization skipped, following/list are already matched.")
                continue

            diff_solve_each_num = slave.diff_solve_each_num
            to_be_added = to_be_added_all[:diff_solve_each_num]
            to_be_added_rest = to_be_added_all[diff_solve_each_num:]
            logger.info(f"Num of to_be_added = {len(to_be_added)}")
            logger.info(f"Num of to_be_added_rest = {len(to_be_added_rest)}")

            to_be_removed = to_be_removed_all[:diff_solve_each_num]
            to_be_removed_rest = to_be_removed_all[diff_solve_each_num:]
            logger.info(f"Num of to_be_removed = {len(to_be_removed)}")
            logger.info(f"Num of to_be_removed_rest = {len(to_be_removed_rest)}")

            list_id = slave.list_id
            logger.info(f"Add to_be_added user -> {dry_run_log}start")
            for user in to_be_added:
                screen_name = user.screen_name
                try:
                    if not self.is_dry_run:
                        slave.twitter.add_list_member(list_id, screen_name)
                    logger.info(f"\t{user}")
                except Exception as e:
                    logger.error(f"{e}")
            logger.info(f"Add to_be_added user -> {dry_run_log}done")

            logger.info(f"Remove to_be_removed user -> {dry_run_log}start")
            for user in to_be_removed:
                screen_name = user.screen_name
                try:
                    if not self.is_dry_run:
                        slave.twitter.remove_list_member(list_id, screen_name)
                    logger.info(f"\t{user}")
                except Exception as e:
                    logger.error(f"{e}")
            logger.info(f"Remove to_be_removed user -> {dry_run_log}done")

            self.config_dict["slave"]["account_list"][i]["list"]["to_be_add"] = [r.to_dict() for r in to_be_added_rest]
            self.config_dict["slave"]["account_list"][i]["list"]["to_be_removed"] = [
                r.to_dict() for r in to_be_removed_rest
            ]
            logger.info("")

        logger.info("Update rest -> start")
        self.config_json_path.write_bytes(orjson.dumps(self.config_dict, option=orjson.OPT_INDENT_2))
        logger.info("Update rest -> done")
        logger.info("Run list_sync -> done")
        return Result.success

    def sync(self) -> Result:
        """sync メイン

        Returns:
            Result: 成功時 Result.success, 失敗時 Result.failed
        """
        horizontal_line = "-" * 80
        half_line = "-" * 40
        logger.info(horizontal_line)
        self.master_sync()
        logger.info(half_line)
        self.following_sync()
        logger.info(half_line)
        self.list_sync()
        logger.info(horizontal_line)
        return Result.success


if __name__ == "__main__":
    config_json: Path = Path("./config/following_syncer_config.json")

    arg_parser = argparse.ArgumentParser(
        prog="Following Syncer", description="Sync master account with slave account."
    )
    arg_parser.add_argument("--dry-run", action="store_true")

    fs = FollowingSyncer(config_json, arg_parser)
    fs.sync()
