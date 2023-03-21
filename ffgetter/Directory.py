# coding: utf-8
import datetime
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from jinja2 import Template

from ffgetter.value_object.DiffRecordList import DiffFollowerList, DiffFollowingList
from ffgetter.value_object.UserRecord import Follower, Following
from ffgetter.value_object.UserRecordList import FollowerList, FollowingList


@dataclass(frozen=True)
class Directory():
    """ディレクトリ操作を司るクラス

    カレントディレクトリはこのファイルが存在する一つ上のディレクトリとなる
    通常は ./FFGetter/ がカレントディレクトリとなる

    Args:
        None

    Attributes:
        base_path (Path): 基準となるパス
        CONFIG_FILE_PATH (str): config 設定ファイルがあるパス
        TEMPLATE_FILE_PATH (str): 出力内容のテンプレートファイルパス, デフォルトは"./ext/template.txt"
        FILE_NAME_BASE (str): 保存する際の基幹ファイル名, デフォルトは"ff_list"
        RESULT_DIRECTORY (str): 保存する際の結果保存ディレクトリ, デフォルトは"./result/"
        BACKUP_DIRECTORY (str): 古い結果を移動させる先のディレクトリ, デフォルトは"./bak/"
    """
    base_path: ClassVar[Path]

    FILE_NAME_BASE = "ff_list"
    TEMPLATE_FILE_PATH = "./ext/template.txt"
    RESULT_DIRECTORY = "./result/"
    BACKUP_DIRECTORY = "./bak/"

    def __post_init__(self) -> None:
        """初期化後処理

        カレントディレクトリをこのファイルが存在する一つ上のディレクトリとして設定する
        """
        object.__setattr__(self, "base_path", Path(os.path.dirname(__file__)).parent)
        self.set_current()

        if not Path(self.TEMPLATE_FILE_PATH).is_file():
            raise FileNotFoundError(f"template file is not found. {self.TEMPLATE_FILE_PATH} is not exist.")
        Path(self.RESULT_DIRECTORY).mkdir(parents=True, exist_ok=True)
        Path(self.BACKUP_DIRECTORY).mkdir(parents=True, exist_ok=True)

    def set_current(self) -> Path:
        """カレントディレクトリを設定する

        Returns:
            base_path (Path): 設定したディレクトリパス
        """
        os.chdir(self.base_path)
        return self.base_path

    def get_last_file_path(self) -> Path | None:
        """前回実行ファイルのパスを取得する

        Returns:
            last_file_path (Path | None): 前回実行ファイルのパス, 存在しないまたは初回実行の場合None
        """
        last_file_path: Path

        # RESULT_DIRECTORY 内の FILE_NAME_BASE をファイル名に持つすべてのファイルパスを取得
        prev_file_path_list = list(Path(self.RESULT_DIRECTORY).glob(f"{self.FILE_NAME_BASE}*"))
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

    def get_last_following(self) -> FollowingList:
        """前回実行ファイル中から following を取得する

        Returns:
            prev_following_list (FollowingList):
                前回実行ファイルから抽出した FollowingList
                前回実行ファイルが存在しない場合も FollowingList は返却されるが、その要素は空となる
        """
        # 前回実行ファイルパス取得
        last_file_path = self.get_last_file_path()
        if not last_file_path:
            return FollowingList.create()

        # 前回実行ファイルを読み込む
        pattern = "^(.*?), (.*), (.*?)$"
        read_flag = False
        prev_following_list = []
        with last_file_path.open("r", encoding="utf-8") as fin:
            for line in fin:
                if not read_flag and re.findall("^following(.*)", line):
                    # following ブロック読み込み開始
                    read_flag = True
                if read_flag and line == "\n":
                    # 空行まで読み込んだら終了
                    break
                if read_flag and (records := re.findall(pattern, line)):
                    record = records[0]
                    if record[0] == "id":
                        continue
                    prev_following = Following.create(
                        record[0],
                        record[1],
                        record[2],
                    )
                    prev_following_list.append(prev_following)
        return FollowingList.create(prev_following_list)

    def get_last_follower(self) -> FollowerList:
        """前回実行ファイル中から follower を取得する

        Returns:
            prev_follower_list (FollowerList):
                前回実行ファイルから抽出した FollowerList
                前回実行ファイルが存在しない場合も FollowerList は返却されるが、その要素は空となる
        """
        # 前回実行ファイルパス取得
        last_file_path = self.get_last_file_path()
        if not last_file_path:
            return FollowerList.create()

        # 前回実行ファイルを読み込む
        pattern = "^(.*?), (.*), (.*?)$"
        read_flag = False
        prev_follower_list = []
        with last_file_path.open("r", encoding="utf-8") as fin:
            for line in fin:
                if not read_flag and re.findall("^follower(.*)", line):
                    # follower ブロック読み込み開始
                    read_flag = True
                if read_flag and line == "\n":
                    # 空行まで読み込んだら終了
                    break
                if read_flag and (records := re.findall(pattern, line)):
                    record = records[0]
                    if record[0] == "id":
                        continue
                    prev_follower = Follower.create(
                        record[0],
                        record[1],
                        record[2],
                    )
                    prev_follower_list.append(prev_follower)
        return FollowerList.create(prev_follower_list)

    def save_file(self,
                  following_list: FollowingList,
                  follower_list: FollowerList,
                  diff_following_list: DiffFollowingList,
                  diff_follower_list: DiffFollowerList) -> Path:
        """結果をファイルに保存する

        Args:
            following_list (FollowingList): 今回取得した FollowingList
            follower_list (FollowerList): 今回取得した FollowerList
            diff_following_list (DiffFollowingList): 前回との差分を格納した DiffFollowingList
            diff_follower_list (DiffFollowerList): 前回との差分を格納した DiffFollowerList

        Returns:
            file_path (Path): 保存したファイルのパス
        """
        # 前回ファイルがあるならパスを取得
        last_file_path: Path | None = self.get_last_file_path()

        # 保存ファイルパスを生成
        today_datetime = datetime.date.today()
        today_str = today_datetime.strftime("%Y%m%d")
        file_path = Path(self.RESULT_DIRECTORY) / f"{self.FILE_NAME_BASE}_{today_str}.txt"

        # 引数のリストを文字列リストに変換
        t_following_list = [r.line + "\n" for r in following_list]
        t_follower_list = [r.line + "\n" for r in follower_list]
        t_diff_following_list = [r.line + "\n" for r in diff_following_list]
        t_diff_follower_list = [r.line + "\n" for r in diff_follower_list]

        # 各プロックのキャプション設定
        following_num = len(t_following_list)
        follower_num = len(t_follower_list)
        following_caption = f"following {following_num}"
        follower_caption = f"follower {follower_num}"
        difference_caption = ""
        if last_file_path:
            difference_caption = f"difference with {last_file_path.name}"
        else:
            difference_caption = f"difference with nothing (first run)"

        # テンプレートファイル読み込み
        template_str = ""
        with Path(self.TEMPLATE_FILE_PATH).open("r") as fin:
            template_str = fin.read()

        # レンダリング
        template: Template = Template(template_str)
        rendered_str = template.render({
            "today_str": today_str,
            "following_caption": following_caption,
            "following_list": t_following_list,
            "follower_caption": follower_caption,
            "follower_list": t_follower_list,
            "difference_caption": difference_caption,
            "diff_following_list": t_diff_following_list,
            "diff_follower_list": t_diff_follower_list,
        })

        # ファイル保存
        with file_path.open("w", encoding="utf-8") as fout:
            fout.write(rendered_str)
        return file_path
    
    def move_old_file(self, reserved_file_num: int) -> list[str] | FileExistsError:
        """古いファイルを移動させる

        RESULT_DIRECTORY に存在する reserved_file_num 個を超える分の古いファイルを
        BACKUP_DIRECTORY に移動させる

        Args:
            reserved_file_num (int): RESULT_DIRECTORY に残すファイル数

        Raises:
            FileExistsError: 移動先に同じ名前のファイルが存在している場合

        Returns:
            moved_list (list[str]): 移動させた後のファイルパスリスト
        """
        if reserved_file_num < 0:
            return []

        result_path = Path(self.RESULT_DIRECTORY)
        backup_path = Path(self.BACKUP_DIRECTORY)
        file_path_list = list(result_path.glob(f"{self.FILE_NAME_BASE}*"))
        if len(file_path_list) <= reserved_file_num:
            return []

        moved_list = []
        to_move_index = len(file_path_list) - reserved_file_num
        to_move_file_list = file_path_list[:to_move_index]
        for to_move_file in to_move_file_list:
            # すでに移動先に同じ名前のファイルが存在している場合は
            # FileExistsError が発生する
            to_move_file.rename(backup_path / to_move_file.name)
            moved_list.append(backup_path / to_move_file.name)
        return moved_list


if __name__ == "__main__":
    directory = Directory()
    print(directory)

    prev_following_list = directory.get_last_following()
    print(len(prev_following_list))
    prev_follower_list = directory.get_last_follower()
    print(len(prev_follower_list))

    from ffgetter.value_object.DiffRecordList import DiffType
    from ffgetter.value_object.ScreenName import ScreenName
    from ffgetter.value_object.UserId import UserId
    from ffgetter.value_object.UserName import UserName
    from ffgetter.value_object.UserRecord import Following
    from ffgetter.value_object.UserRecordList import FollowerList, FollowingList
    diff_type = DiffType.ADD
    user_id = UserId(123)
    user_name = UserName("ユーザー1")
    screen_name = ScreenName("screen_name_1")
    following = Following(user_id, user_name, screen_name)
    following1 = Following(UserId(1), user_name, screen_name)
    following2 = Following(UserId(2), user_name, screen_name)
    following_list1 = FollowingList.create([following, following1])
    following_list2 = FollowingList.create([following, following2])
    diff_following = DiffFollowingList.create_from_diff(following_list1, following_list2)
    rendered_str = directory.save_file(prev_following_list, prev_follower_list, diff_following, diff_following)
    print(rendered_str)

    # res = directory.move_old_file(10)
    # print(res)
