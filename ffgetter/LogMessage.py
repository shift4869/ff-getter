# coding: utf-8
from enum import Enum


class Message(Enum):
    """ログメッセージを表す列挙型
        関数呼び出し()で値を取得できる
        cx: Message.HORIZONTAL_LINE()
    """
    HORIZONTAL_LINE = "-" * 80

    APPLICATION_START = "ffgetter -> start"
    APPLICATION_DONE = "ffgetter -> done"
    APPLICATION_MULTIPLE_RUN = "ffgetter is now running. This instance is not start."

    CORE_INIT_START = "Core init -> start"
    CORE_INIT_DONE = "Core init -> done"
    CORE_RUN_START = "Core run -> start"
    CORE_RUN_DONE = "Core run -> done"

    USE_API_MODE = "Use API mode ..."
    NO_API_MODE = "No API mode ..."

    GET_FOLLOWING_LIST_START = "Getting following list -> start"
    GET_FOLLOWING_LIST_DONE = "Getting following list-> done"

    GET_FOLLOWER_LIST_START = "Getting follower list -> start"
    GET_FOLLOWER_LIST_DONE = "Getting follower list-> done"

    GET_PREV_FOLLOWING_LIST_START = "Getting prev following list -> start"
    GET_PREV_FOLLOWING_LIST_DONE = "Getting prev following list -> done"

    GET_PREV_FOLLOWER_LIST_START = "Getting prev follower list -> start"
    GET_PREV_FOLLOWER_LIST_DONE = "Getting prev follower list -> done"

    GET_DIFF_FOLLOWING_LIST_START = "Diff following list -> start"
    GET_DIFF_FOLLOWING_LIST_DONE = "Diff following list -> done"

    GET_DIFF_FOLLOWER_LIST_START = "Diff follower list -> start"
    GET_DIFF_FOLLOWER_LIST_DONE = "Diff follower list -> done"

    SAVE_RESULT_START = "Save result to file -> start"
    SAVE_RESULT_DONE = "Save result to file -> done"

    MOVE_OLD_FILE_START = "Move old file -> start"
    MOVE_OLD_FILE_DONE = "Move old file -> done"
    MOVE_OLD_FILE_PATH = "Moved file: {}"

    RESULT_FILE_OPENING = "Result file: {} opened."

    DIRECTORY_INIT_START = "Directory init -> start"
    DIRECTORY_INIT_DONE = "Directory init -> done"
    SET_CURRENT_DIRECTORY = "Set current directory: {}"

    def __call__(self) -> str:
        return str(self.value)


if __name__ == "__main__":
    print(Message.HORIZONTAL_LINE())
    print(Message.APPLICATION_START())
    print(Message.APPLICATION_DONE())
    print(Message.HORIZONTAL_LINE())
