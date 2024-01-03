from dataclasses import dataclass
from typing import Iterable, Iterator, Self

from ff_getter.value_object.user_record import Follower, Following, UserRecord


@dataclass(frozen=True)
class UserRecordList(Iterable):
    """レコードリスト

    Args:
        _list (list[UserRecord]): レコードのリスト
    """

    _list: list[UserRecord]

    def __post_init__(self) -> None:
        if not isinstance(self._list, list):
            raise TypeError("arg list must be list[UserRecord].")
        if not all([isinstance(r, UserRecord) for r in self._list]):
            raise TypeError("arg list must be list[UserRecord].")

    def __iter__(self) -> Iterator[UserRecord]:
        return self._list.__iter__()

    def __next__(self) -> UserRecord | StopIteration:
        return self._list.__next__()

    def __len__(self) -> int:
        return self._list.__len__()

    @classmethod
    def create(cls, user_record_list: list[UserRecord] | UserRecord | None = None) -> Self:
        """レコードリスト作成

        引数の型を見てレコードリストを作成する
        None の場合は要素が空のレコードリストを返す

        Args:
            user_record_list (list[UserRecord], UserRecord, optional):
                レコードのリスト, レコード, None のいずれか

        Returns:
            Self: レコードリスト
        """
        if isinstance(user_record_list, list):
            if all([isinstance(r, UserRecord) for r in user_record_list]):
                return cls(user_record_list)
        if isinstance(user_record_list, UserRecord):
            user_record = user_record_list
            return cls([user_record])
        return cls([])


@dataclass(frozen=True)
class FollowingList(UserRecordList):
    """Following レコードリスト"""

    pass


@dataclass(frozen=True)
class FollowerList(UserRecordList):
    """Follower レコードリスト"""

    pass


if __name__ == "__main__":
    from ff_getter.value_object.screen_name import ScreenName
    from ff_getter.value_object.user_id import UserId
    from ff_getter.value_object.user_name import UserName

    user_id = UserId(123)
    user_name = UserName("ユーザー1")
    screen_name = ScreenName("screen_name_1")
    user_record = UserRecord(user_id, user_name, screen_name)
    user_record_list = UserRecordList([user_record])
    print(user_record_list)
    for r in user_record_list:
        print(r)

    user_record_list = UserRecordList.create([user_record])
    print(user_record_list)

    user_record_list = UserRecordList.create(user_record)
    print(user_record_list)

    user_record_list = UserRecordList.create([])
    print(user_record_list)

    user_record_list = UserRecordList.create()
    print(user_record_list)

    following = Following(user_id, user_name, screen_name)
    following_list = FollowingList.create([following])
    print(following_list)

    follower = Follower(user_id, user_name, screen_name)
    follower_list = FollowerList.create([follower])
    print(follower_list)
