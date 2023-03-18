# coding: utf-8
from dataclasses import dataclass
from typing import Iterable, Iterator, Self

from ffgetter.value_object.UserRecord import Follower, Following, UserRecord


@dataclass(frozen=True)
class UserRecordList(Iterable):
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
        if isinstance(user_record_list, list):
            if all([isinstance(r, UserRecord) for r in user_record_list]):
                return cls(user_record_list)
        if isinstance(user_record_list, UserRecord):
            user_record = user_record_list
            return cls([user_record])
        return cls([])


@dataclass(frozen=True)
class FollowingList(UserRecordList):
    pass


@dataclass(frozen=True)
class FollowerList(UserRecordList):
    pass


if __name__ == "__main__":
    from ffgetter.value_object.ScreenName import ScreenName
    from ffgetter.value_object.UserId import UserId
    from ffgetter.value_object.UserName import UserName

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