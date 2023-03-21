# coding: utf-8
from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Iterator, Self

from ffgetter.value_object.DiffRecord import DiffFollower, DiffFollowing, DiffRecord, DiffType
from ffgetter.value_object.UserRecordList import UserRecordList


@dataclass(frozen=True)
class DiffRecordList(Iterable):
    """差分レコードリスト

    Args:
        _list (list[DiffRecord]): 差分レコードのリスト
    """
    _list: list[DiffRecord]

    def __post_init__(self) -> None:
        if not isinstance(self._list, list):
            raise TypeError("arg list must be list[DiffRecord].")
        if not all([isinstance(r, DiffRecord) for r in self._list]):
            raise TypeError("arg list must be list[DiffRecord].")

    def __iter__(self) -> Iterator[DiffRecord]:
        return self._list.__iter__()

    def __next__(self) -> DiffRecord | StopIteration:
        return self._list.__next__()

    def __len__(self) -> int:
        return self._list.__len__()

    @classmethod
    def create(cls, diff_record_list: list[DiffRecord] | DiffRecord | None = None) -> Self:
        """差分レコードリスト作成

        引数の型を見て差分レコードリストを作成する
        None の場合は要素が空の差分レコードリストを返す

        Args:
            diff_record_list (list[DiffRecord], DiffRecord, optional):
                差分レコードのリスト, 差分レコード, None のいずれか

        Returns:
            Self: 差分レコードリスト
        """
        if isinstance(diff_record_list, list):
            if all([isinstance(r, DiffRecord) for r in diff_record_list]):
                return cls(diff_record_list)
        if isinstance(diff_record_list, DiffRecord):
            diff_record = diff_record_list
            return cls([diff_record])
        return cls([])

    @classmethod
    def create_from_diff(cls, p_list: UserRecordList, q_list: UserRecordList) -> Self:
        """2つのレコードリストから差分レコードリストを作成する

        p_list, q_list のどちらかが空ならば、空の差分レコードリストを返す
        p_list, q_list の要素のIDをそれぞれ収集し、排他的論理和にて差分を得る
        p_list に存在するが q_list に存在しないものは DiffType.ADD,
        p_list に存在しないが q_list に存在するものは DiffType.REMOVE が割り当てられる

        Args:
            p_list (UserRecordList): レコードリスト(基準)
            q_list (UserRecordList): レコードリスト(変更後想定)

        Returns:
            Self: 差分レコードリスト
        """
        p1_list = deepcopy(p_list)
        q1_list = deepcopy(q_list)

        p2_list = [r.to_dict() for r in p1_list]
        q2_list = [r.to_dict() for r in q1_list]

        # 引数のどちらかが空なら空の差分リストを返す
        if not (p2_list and q2_list):
            return cls.create()

        # 順序保持用の order_id を付与
        for i, p in enumerate(p2_list):
            p["order_id"] = i
        for i, q in enumerate(q2_list):
            q["order_id"] = i + len(p2_list) + 1

        p = [r["id"] for r in p2_list]
        q = [r["id"] for r in q2_list]

        result: list[dict] = []
        # 集合演算：排他的論理和
        diff_list = set(p) ^ set(q)
        for diff_id in diff_list:
            if diff_id in p:
                record = [r for r in p2_list if r["id"] == diff_id][0]
                record["diff_type"] = "ADD"
                result.append(record)
            elif diff_id in q:
                record = [r for r in q2_list if r["id"] == diff_id][0]
                record["diff_type"] = "REMOVE"
                result.append(record)
        result.sort(key=lambda r: r["order_id"])

        diff_record_list = [
            DiffRecord.create(
                r.get("diff_type"),
                r.get("id"),
                r.get("name"),
                r.get("screen_name"),
            )
            for r in result
        ]
        return cls.create(diff_record_list)


@dataclass(frozen=True)
class DiffFollowingList(DiffRecordList):
    """Following 差分レコードリスト
    """
    pass


@dataclass(frozen=True)
class DiffFollowerList(DiffRecordList):
    """Follower 差分レコードリスト
    """
    pass


if __name__ == "__main__":
    from ffgetter.value_object.ScreenName import ScreenName
    from ffgetter.value_object.UserId import UserId
    from ffgetter.value_object.UserName import UserName

    diff_type = DiffType.ADD
    user_id = UserId(123)
    user_name = UserName("ユーザー1")
    screen_name = ScreenName("screen_name_1")
    diff_record = DiffRecord(diff_type, user_id, user_name, screen_name)
    diff_record_list = DiffRecordList([diff_record])
    print(diff_record_list)
    for r in diff_record_list:
        print(r)

    diff_record_list = DiffRecordList.create([diff_record])
    print(diff_record_list)

    diff_record_list = DiffRecordList.create(diff_record)
    print(diff_record_list)

    diff_record_list = DiffRecordList.create([])
    print(diff_record_list)

    diff_record_list = DiffRecordList.create()
    print(diff_record_list)

    diff_following = DiffFollowing(diff_type, user_id, user_name, screen_name)
    diff_following_list = DiffFollowingList.create([diff_following])
    print(diff_following_list)

    diff_type = DiffType.REMOVE
    diff_follower = DiffFollower(diff_type, user_id, user_name, screen_name)
    diff_follower_list = DiffFollowerList.create([diff_follower])
    print(diff_follower_list)

    from ffgetter.value_object.UserRecord import Following
    from ffgetter.value_object.UserRecordList import FollowerList, FollowingList
    following = Following(user_id, user_name, screen_name)
    following1 = Following(UserId(1), user_name, screen_name)
    following2 = Following(UserId(2), user_name, screen_name)
    following_list1 = FollowingList.create([following, following1])
    following_list2 = FollowingList.create([following, following2])
    diff_following = DiffFollowingList.create_from_diff(following_list1, following_list2)
    print(diff_following)
