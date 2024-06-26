
from dataclasses import dataclass
from logging import INFO, getLogger
from typing import Self

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class User:
    rest_id: str
    name: str
    screen_name: str
    protected: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.rest_id, str):
            raise ValueError("rest_id must be str.")
        if not isinstance(self.name, str):
            raise ValueError("name must be str.")
        if not isinstance(self.screen_name, str):
            raise ValueError("screen_name must be str.")
        if not isinstance(self.protected, bool):
            raise ValueError("protected must be bool.")

    def __repr__(self) -> str:
        return f"rest_id={self.rest_id}, name={self.name}, screen_name={self.screen_name}, protected={self.protected}"

    def to_dict(self) -> dict:
        return {
            "rest_id": self.rest_id,
            "name": self.name,
            "screen_name": self.screen_name,
        }


class FollowingUser(User):
    @classmethod
    def create(cls, user: User) -> Self:
        return FollowingUser(user.rest_id, user.name, user.screen_name, user.protected)


class ListUser(User):
    @classmethod
    def create(cls, user: User) -> Self:
        return ListUser(user.rest_id, user.name, user.screen_name, user.protected)


if __name__ == "__main__":
    user = User("12345678", "test_user🎉", "test_user")
    user = FollowingUser("12345678", "test_user🎉", "test_user")
    user = ListUser("12345678", "test_user🎉", "test_user")
