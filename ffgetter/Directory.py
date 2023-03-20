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
    base_path: ClassVar[Path]

    FILE_NAME_BASE = "ff_list"
    RESULT_DIRECTORY = "./result/"
    BACKUP_DIRECTORY = "./bak/"
    TEMPLATE_FILE_PATH = "./ext/template.txt"

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_path", Path(os.path.dirname(__file__)).parent)
        self.set_current()

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
            last_file_path (Path | None): 前回実行ファイルのパス, 存在しない場合None
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
        """
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
        """
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
                  diff_follower_list: DiffFollowerList) -> str:
        """結果をファイルに保存
        """
        last_file_path: Path | None = self.get_last_file_path()

        today_datetime = datetime.date.today()
        today_str = today_datetime.strftime("%Y%m%d")
        file_path = Path(self.RESULT_DIRECTORY) / f"{self.FILE_NAME_BASE}_{today_str}.txt"

        t_following_list = [r.line + "\n" for r in following_list]
        t_follower_list = [r.line + "\n" for r in follower_list]
        t_diff_following_list = [r.line + "\n" for r in diff_following_list]
        t_diff_follower_list = [r.line + "\n" for r in diff_follower_list]

        following_num = len(t_following_list)
        follower_num = len(t_follower_list)
        following_caption = f"following {following_num}"
        follower_caption = f"follower {follower_num}"
        difference_caption = ""
        if last_file_path:
            difference_caption = f"difference with {last_file_path.name}"
        else:
            difference_caption = f"difference with nothing (first run)"

        template_str = ""
        with Path(self.TEMPLATE_FILE_PATH).open("r") as fin:
            template_str = fin.read()

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

        with file_path.open("w", encoding="utf-8") as fout:
            fout.write(rendered_str)
        return rendered_str


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
