# coding: utf-8
from dataclasses import dataclass
from enum import Enum
from typing import Self

from ffgetter.value_object.ScreenName import ScreenName
from ffgetter.value_object.UserId import UserId
from ffgetter.value_object.UserName import UserName


class DiffType(Enum):
    """差分タイプ
    """
    ADD = "ADD"
    REMOVE = "REMOVE"


@dataclass(frozen=True)
class DiffRecord():
    """差分レコード

    Args:
        _diff_type (DiffType): 差分タイプ
        _id (UserId): ユーザID
        _name (UserName): ユーザ名
        _screen_name (ScreenName): スクリーンネーム
    """
    _diff_type: DiffType
    _id: UserId
    _name: UserName
    _screen_name: ScreenName

    def __post_init__(self) -> None:
        if not isinstance(self._diff_type, DiffType):
            raise TypeError("diff_type must be DiffType.")
        if not isinstance(self._id, UserId):
            raise TypeError("id must be UserId.")
        if not isinstance(self._name, UserName):
            raise TypeError("name must be UserName.")
        if not isinstance(self._screen_name, ScreenName):
            raise TypeError("screen_name must be ScreenName.")

    @property
    def diff_type(self) -> DiffType:
        return self._diff_type

    @property
    def id(self) -> UserId:
        return self._id

    @property
    def name(self) -> UserName:
        return self._name

    @property
    def screen_name(self) -> ScreenName:
        return self._screen_name

    @property
    def line(self) -> str:
        """レコードを1行として文字列に変換

        Returns:
            str: カンマ区切りの1行文字列
        """
        data_line = "{}, {}, {}, {}".format(
            self._diff_type.value,
            self._id.id_str,
            self._name.name,
            self._screen_name.name,
        )
        return data_line

    @classmethod
    def create(cls, diff_type_str: str, id_str: str, name: str, screen_name: str) -> Self:
        """差分レコード作成

        Args:
            diff_type_str (str): 差分タイプ
            id_str (str): ユーザID
            name (str): ユーザ名
            screen_name (str): スクリーンネーム

        Returns:
            Self : 差分レコードインスタンス
        """
        diff_type = None
        if diff_type_str == "ADD":
            diff_type = DiffType.ADD
        elif diff_type_str == "REMOVE":
            diff_type = DiffType.REMOVE
        else:
            raise ValueError("diff_type_str must be in ['ADD', 'REMOVE'].")
        user_id = UserId(int(id_str))
        user_name = UserName(name)
        screen_name = ScreenName(screen_name)
        return cls(diff_type, user_id, user_name, screen_name)


@dataclass(frozen=True)
class DiffFollowing(DiffRecord):
    """Following 差分レコード
    """
    pass


@dataclass(frozen=True)
class DiffFollower(DiffRecord):
    """Follower 差分レコード
    """
    pass


if __name__ == "__main__":
    diff_type = DiffType.ADD
    user_id = UserId(123)
    user_name = UserName("ユーザー1")
    screen_name = ScreenName("screen_name_1")
    diff_record = DiffRecord(diff_type, user_id, user_name, screen_name)
    print(diff_record)
    print(diff_record.line)

    diff_following = DiffFollowing(diff_type, user_id, user_name, screen_name)
    print(diff_following)
    print(diff_following.line)
    print(isinstance(diff_following, DiffFollowing))
    print(isinstance(diff_following, DiffFollower))

    diff_following = DiffFollowing.create("ADD", user_id.id, user_name.name, screen_name.name)
    print(diff_following)
    print(diff_following.line)
    print(isinstance(diff_following, DiffFollowing))
    print(isinstance(diff_following, DiffFollower))

    diff_type = DiffType.REMOVE
    diff_follower = DiffFollower(diff_type, user_id, user_name, screen_name)
    print(diff_follower)
    print(diff_follower.line)
    print(isinstance(diff_follower, DiffFollowing))
    print(isinstance(diff_follower, DiffFollower))

    diff_follower = DiffFollower.create("REMOVE", user_id.id, user_name.name, screen_name.name)
    print(diff_follower)
    print(diff_follower.line)
    print(isinstance(diff_follower, DiffFollowing))
    print(isinstance(diff_follower, DiffFollower))
