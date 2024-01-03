from dataclasses import dataclass
from typing import Self

from ffgetter.value_object.screen_name import ScreenName
from ffgetter.value_object.user_id import UserId
from ffgetter.value_object.user_name import UserName


@dataclass(frozen=True)
class UserRecord():
    """レコード

    Args:
        _id (UserId): ユーザID
        _name (UserName): ユーザ名
        _screen_name (ScreenName): スクリーンネーム
    """
    _id: UserId
    _name: UserName
    _screen_name: ScreenName

    def __post_init__(self) -> None:
        if not isinstance(self._id, UserId):
            raise TypeError("id must be UserId.")
        if not isinstance(self._name, UserName):
            raise TypeError("name must be UserName.")
        if not isinstance(self._screen_name, ScreenName):
            raise TypeError("screen_name must be ScreenName.")

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
        data_line = "{}, {}, {}".format(
            self._id.id_str,
            self._name.name,
            self._screen_name.name,
        )
        return data_line

    def to_dict(self) -> dict:
        return {
            "id": self._id.id_str,
            "name": self._name.name,
            "screen_name": self._screen_name.name,
        }

    @classmethod
    def create(cls, id_str: str, name: str, screen_name: str) -> Self:
        """レコード作成
        """
        user_id = UserId(int(id_str))
        user_name = UserName(name)
        screen_name = ScreenName(screen_name)
        return cls(user_id, user_name, screen_name)


@dataclass(frozen=True)
class Following(UserRecord):
    """Following レコード
    """
    pass


@dataclass(frozen=True)
class Follower(UserRecord):
    """Follower レコード
    """
    pass


if __name__ == "__main__":
    user_id = UserId(123)
    user_name = UserName("ユーザー1")
    screen_name = ScreenName("screen_name_1")
    user_record = UserRecord(user_id, user_name, screen_name)
    print(user_record)
    print(user_record.line)

    following = Following(user_id, user_name, screen_name)
    print(following)
    print(following.line)
    print(isinstance(following, Following))
    print(isinstance(following, Follower))

    following = Following.create(user_id.id, user_name.name, screen_name.name)
    print(following)
    print(following.line)
    print(isinstance(following, Following))
    print(isinstance(following, Follower))

    follower = Follower(user_id, user_name, screen_name)
    print(follower)
    print(follower.line)
    print(isinstance(follower, Following))
    print(isinstance(follower, Follower))

    follower = Follower.create(user_id.id, user_name.name, screen_name.name)
    print(follower)
    print(follower.line)
    print(isinstance(follower, Following))
    print(isinstance(follower, Follower))
