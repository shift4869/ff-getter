import sys
import unittest
from collections import namedtuple

from mock import MagicMock, patch
from twitter.constants import Operation
from twitter.util import get_headers

from following_syncer.twitter_api import TwitterAPI


class TestTwitterAPI(unittest.TestCase):
    def setUp(self) -> None:
        mock_logger = self.enterContext(patch("following_syncer.twitter_api.logger"))
        self.mock_scraper = self.enterContext(patch("following_syncer.twitter_api.Scraper"))
        self.mock_account = self.enterContext(patch("following_syncer.twitter_api.Account"))
        return super().setUp()

    def _get_instance(self) -> TwitterAPI:
        instance = TwitterAPI("dummy_ct0", "dummy_auth_token", "dummy_target_screen_name")
        return instance

    def test_init(self):
        instance = TwitterAPI("dummy_ct0", "dummy_auth_token", "dummy_target_screen_name")
        self.assertEqual("dummy_ct0", instance.ct0)
        self.assertEqual("dummy_auth_token", instance.auth_token)
        self.assertEqual("dummy_target_screen_name", instance.target_screen_name)

        with self.assertRaises(TypeError):
            instance = TwitterAPI(-1, "dummy_auth_token", "dummy_target_screen_name")
        with self.assertRaises(TypeError):
            instance = TwitterAPI("dummy_ct0", -1, "dummy_target_screen_name")
        with self.assertRaises(TypeError):
            instance = TwitterAPI("dummy_ct0", "dummy_auth_token", -1)

    def test_scraper(self):
        instance = self._get_instance()
        actual = instance.scraper
        self.mock_scraper.assert_called_once_with(
            cookies={"ct0": instance.ct0, "auth_token": instance.auth_token}, pbar=False
        )
        self.assertEqual(self.mock_scraper.return_value, actual)
        self.mock_scraper.reset_mock()

        actual = instance.scraper
        self.mock_scraper.assert_not_called()
        self.assertTrue(hasattr(instance, "_scraper"))
        self.assertEqual(self.mock_scraper.return_value, actual)

    def test_account(self):
        instance = self._get_instance()
        actual = instance.account
        self.mock_account.assert_called_once_with(
            cookies={"ct0": instance.ct0, "auth_token": instance.auth_token}, pbar=False
        )
        self.assertEqual(self.mock_account.return_value, actual)
        self.mock_account.reset_mock()

        actual = instance.account
        self.mock_account.assert_not_called()
        self.assertTrue(hasattr(instance, "_account"))
        self.assertEqual(self.mock_account.return_value, actual)

    def test_target_id(self):
        mock_lookup = self.enterContext(patch("following_syncer.twitter_api.TwitterAPI.lookup_user_by_screen_name"))
        mock_lookup.side_effect = lambda target_screen_name: {"rest_id": 0}

        instance = self._get_instance()
        actual = instance.target_id
        mock_lookup.assert_called_once_with(instance.target_screen_name)
        self.assertEqual(0, actual)
        mock_lookup.reset_mock()

        actual = instance.target_id
        mock_lookup.assert_not_called()
        self.assertTrue(hasattr(instance, "_target_id"))
        self.assertEqual(0, actual)

    def test_lookup_user_by_screen_name(self):
        def users_return(screen_name_list):
            dummy_result = {f"dummy_screen_name_{i}": {"dummy_lookup": f"user_{i}"} for i in range(5)}
            screen_name = screen_name_list[0]
            return [dummy_result[screen_name]]

        mock_users: MagicMock = self.mock_scraper.return_value.users
        mock_users.side_effect = users_return
        instance = self._get_instance()
        for i in range(5):
            actual = instance.lookup_user_by_screen_name(f"dummy_screen_name_{i}")
            expect = {"dummy_lookup": f"user_{i}"}
            self.assertEqual(expect, actual)
            mock_users.assert_any_call([f"dummy_screen_name_{i}"])

        mock_users.reset_mock()
        for i in range(5):
            actual = instance.lookup_user_by_screen_name(f"dummy_screen_name_{i}")
            expect = {"dummy_lookup": f"user_{i}"}
            self.assertEqual(expect, actual)
            mock_users.assert_not_called()

    def test_get_likes(self):
        mock_lookup = self.enterContext(patch("following_syncer.twitter_api.TwitterAPI.lookup_user_by_screen_name"))
        mock_likes: MagicMock = self.mock_scraper.return_value.likes
        target_screen_name = "dummy_screen_name"
        limit = 300

        Params = namedtuple("Params", ["is_entry", "is_diff_dict", "is_data_dict", "min_id"])

        def make_expect(params: Params, instance: TwitterAPI) -> list[dict]:
            if params.is_entry:
                data_dict = {"rest_id": "11111"}
                if not params.is_data_dict:
                    return []
                else:
                    return [{"result": data_dict}]
            return []

        def pre_run(params: Params, instance: TwitterAPI) -> TwitterAPI:
            mock_lookup.reset_mock()
            mock_lookup.side_effect = lambda screen_name: [{"rest_id": "0"}]

            mock_likes.reset_mock()
            if params.is_entry:
                data_dict = {"rest_id": "11111"}
                result_dict = {}
                if not params.is_data_dict:
                    result_dict = {}
                elif params.is_diff_dict:
                    result_dict = {"result": {"tweet": data_dict}}
                else:
                    result_dict = {"result": data_dict}

                entry_lists = {"entries": [{"tweet_results": result_dict}]}
                mock_likes.side_effect = lambda target_id_list, limit: entry_lists
            else:
                pass
            return instance

        def post_run(params: Params, instance: TwitterAPI) -> None:
            mock_lookup.assert_called_once_with(target_screen_name)
            mock_likes.assert_called_once_with([0], limit=limit)

        params_list = [
            Params(False, False, False, -1),
            Params(True, False, False, -1),
            Params(True, True, False, -1),
            Params(True, True, True, -1),
            Params(True, False, True, -1),
            Params(True, False, True, 11111),
            Params(True, False, True, 22222),
        ]
        for params in params_list:
            instance = self._get_instance()
            instance = pre_run(params, instance)
            if not params.is_entry:
                with self.assertRaises(ValueError):
                    actual = instance.get_likes(target_screen_name, limit, params.min_id)
            else:
                actual = instance.get_likes(target_screen_name, limit, params.min_id)
                expect = make_expect(params, instance)
                self.assertEqual(expect, actual)
            post_run(params, instance)

    def test_get_user_timeline(self):
        mock_lookup = self.enterContext(patch("following_syncer.twitter_api.TwitterAPI.lookup_user_by_screen_name"))
        mock_timeline: MagicMock = self.mock_scraper.return_value.tweets_and_replies
        target_screen_name = "dummy_screen_name"
        limit = 300

        Params = namedtuple("Params", ["is_entry", "is_diff_dict", "is_data_dict", "min_id"])

        def make_expect(params: Params, instance: TwitterAPI) -> list[dict]:
            if params.is_entry:
                data_dict = {"rest_id": "11111"}
                if not params.is_data_dict:
                    return []
                else:
                    return [{"result": data_dict}]
            return []

        def pre_run(params: Params, instance: TwitterAPI) -> TwitterAPI:
            mock_lookup.reset_mock()
            mock_lookup.side_effect = lambda screen_name: [{"rest_id": "0"}]

            mock_timeline.reset_mock()
            if params.is_entry:
                data_dict = {"rest_id": "11111"}
                result_dict = {}
                if not params.is_data_dict:
                    result_dict = {}
                elif params.is_diff_dict:
                    result_dict = {"result": {"tweet": data_dict}}
                else:
                    result_dict = {"result": data_dict}

                entry_lists = {"entries": [{"tweet_results": result_dict}]}
                mock_timeline.side_effect = lambda target_id_list, limit: entry_lists
            else:
                pass
            return instance

        def post_run(params: Params, instance: TwitterAPI) -> None:
            mock_lookup.assert_called_once_with(target_screen_name)
            mock_timeline.assert_called_once_with([0], limit=limit)

        params_list = [
            Params(False, False, False, -1),
            Params(True, False, False, -1),
            Params(True, True, False, -1),
            Params(True, True, True, -1),
            Params(True, False, True, -1),
            Params(True, False, True, 11111),
            Params(True, False, True, 22222),
        ]
        for params in params_list:
            instance = self._get_instance()
            instance = pre_run(params, instance)
            if not params.is_entry:
                with self.assertRaises(ValueError):
                    actual = instance.get_user_timeline(target_screen_name, limit, params.min_id)
            else:
                actual = instance.get_user_timeline(target_screen_name, limit, params.min_id)
                expect = make_expect(params, instance)
                self.assertEqual(expect, actual)
            post_run(params, instance)

    def test_post_tweet(self):
        mock_tweet: MagicMock = self.mock_account.return_value.tweet
        tweet_str = "dummy_tweet_str"
        instance = self._get_instance()
        actual = instance.post_tweet(tweet_str)
        mock_tweet.assert_called_once_with(tweet_str)
        self.assertEqual(mock_tweet.return_value, actual)

    def test_delete_tweet(self):
        mock_untweet: MagicMock = self.mock_account.return_value.untweet
        tweet_id = "11111"
        instance = self._get_instance()
        actual = instance.delete_tweet(tweet_id)
        mock_untweet.assert_called_once_with(int(tweet_id))
        self.assertEqual(mock_untweet.return_value, actual)

    def test_lookup_tweet(self):
        mock_tweets_by_id: MagicMock = self.mock_scraper.return_value.tweets_by_id
        mock_tweets_by_id.side_effect = lambda tweet_ids: tweet_ids
        tweet_id = "11111"
        instance = self._get_instance()
        actual = instance.lookup_tweet(tweet_id)
        mock_tweets_by_id.assert_called_once_with([int(tweet_id)])
        self.assertEqual(int(tweet_id), actual)

    def test_get_following_list(self):
        mock_lookup = self.enterContext(patch("following_syncer.twitter_api.TwitterAPI.lookup_user_by_screen_name"))
        mock_lookup.side_effect = lambda screen_name: [{"rest_id": "11111"}]
        mock_following: MagicMock = self.mock_scraper.return_value.following
        mock_following.side_effect = lambda screen_name: [{"user_results": "dummy_user_results"}]
        instance = self._get_instance()
        actual = instance.get_following_list()
        mock_following.assert_called_once_with([11111])
        self.assertEqual(["dummy_user_results"], actual)

    def test_get_follower_list(self):
        mock_lookup = self.enterContext(patch("following_syncer.twitter_api.TwitterAPI.lookup_user_by_screen_name"))
        mock_lookup.side_effect = lambda screen_name: [{"rest_id": "11111"}]
        mock_followers: MagicMock = self.mock_scraper.return_value.followers
        mock_followers.side_effect = lambda screen_name: [{"user_results": "dummy_user_results"}]
        instance = self._get_instance()
        actual = instance.get_follower_list()
        mock_followers.assert_called_once_with([11111])
        self.assertEqual(["dummy_user_results"], actual)

    def test_follow(self):
        mock_follow: MagicMock = self.mock_account.return_value.follow
        user_id = "11111"
        instance = self._get_instance()
        actual = instance.follow(user_id)
        mock_follow.assert_called_once_with(int(user_id))
        self.assertEqual(mock_follow.return_value, actual)

    def test_remove(self):
        mock_unfollow: MagicMock = self.mock_account.return_value.unfollow
        user_id = "11111"
        instance = self._get_instance()
        actual = instance.remove(user_id)
        mock_unfollow.assert_called_once_with(int(user_id))
        self.assertEqual(mock_unfollow.return_value, actual)

    def test_get_list_member(self):
        mock_list_member: MagicMock = self.mock_scraper.return_value._run
        mock_list_member.side_effect = lambda ope, queries: [{"user_results": "dummy_user_results"}]
        ope = {"listId": str}, Operation.ListMembers[0], Operation.ListMembers[1]
        list_id = "11111"
        instance = self._get_instance()
        actual = instance.get_list_member(list_id)
        mock_list_member.assert_called_once_with(ope, [str(list_id)])
        self.assertEqual(["dummy_user_results"], actual)

    def test_add_list_member(self):
        mock_lookup = self.enterContext(patch("following_syncer.twitter_api.TwitterAPI.lookup_user_by_screen_name"))
        mock_lookup.side_effect = lambda screen_name: [{"rest_id": "11111"}]
        mock_add_list_member: MagicMock = self.mock_account.return_value.add_list_member
        mock_add_list_member.side_effect = lambda list_id, user_id: [{"user_results": "dummy_user_results"}]
        list_id = "22222"
        screen_name = "dummy_screen_name"
        instance = self._get_instance()
        actual = instance.add_list_member(list_id, screen_name)
        mock_add_list_member.assert_called_once_with(int(list_id), int("11111"))
        self.assertEqual("dummy_user_results", actual)

    def test_remove_list_member(self):
        mock_lookup = self.enterContext(patch("following_syncer.twitter_api.TwitterAPI.lookup_user_by_screen_name"))
        mock_lookup.side_effect = lambda screen_name: [{"rest_id": "11111"}]
        mock_remove_list_member: MagicMock = self.mock_account.return_value.remove_list_member
        mock_remove_list_member.side_effect = lambda list_id, user_id: [{"user_results": "dummy_user_results"}]
        list_id = "22222"
        screen_name = "dummy_screen_name"
        instance = self._get_instance()
        actual = instance.remove_list_member(list_id, screen_name)
        mock_remove_list_member.assert_called_once_with(int(list_id), int("11111"))
        self.assertEqual("dummy_user_results", actual)

    def test_get_mute_keyword_list(self):
        mock_respone = MagicMock()
        mock_respone.json.return_value = "dummy_respone"
        mock_session: MagicMock = self.mock_account.return_value.session.get
        mock_session.side_effect = lambda url, headers, params: mock_respone
        path = "mutes/keywords/list.json"
        params = {}
        instance = self._get_instance()
        headers = get_headers(instance.account.session)
        actual = instance.get_mute_keyword_list()
        mock_session.assert_called_once_with(f"{instance.account.v1_api}/{path}", headers=headers, params=params)
        self.assertEqual("dummy_respone", actual)

    def test_mute_keyword(self):
        mock_v1: MagicMock = self.mock_account.return_value.v1
        mock_v1.side_effect = lambda path, params: "dummy_respone"
        keyword = "dummy_keyword"
        path = "mutes/keywords/create.json"
        payload = {
            "keyword": keyword,
            "mute_surfaces": "notifications,home_timeline,tweet_replies",
            "mute_option": "",
            "duration": "",
        }
        instance = self._get_instance()
        actual = instance.mute_keyword(keyword)
        mock_v1.assert_called_once_with(path, payload)
        self.assertEqual("dummy_respone", actual)

    def test_unmute_keyword(self):
        mock_keyword_dict = {"muted_keywords": [{"keyword": "dummy_keyword", "id": "dummy_keyword_id"}]}
        mock_get_mute_keyword_list = self.enterContext(
            patch("following_syncer.twitter_api.TwitterAPI.get_mute_keyword_list")
        )
        mock_get_mute_keyword_list.side_effect = lambda: mock_keyword_dict
        mock_v1: MagicMock = self.mock_account.return_value.v1
        mock_v1.side_effect = lambda path, params: "dummy_respone"
        keyword = "dummy_keyword"
        path = "mutes/keywords/destroy.json"
        payload = {
            "ids": "dummy_keyword_id",
        }
        instance = self._get_instance()
        actual = instance.unmute_keyword(keyword)
        mock_v1.assert_called_once_with(path, payload)
        self.assertEqual("dummy_respone", actual)

        mock_keyword_dict = {
            "muted_keywords": [
                {"keyword": "dummy_keyword", "id": "dummy_keyword_id"},
                {"keyword": "dummy_keyword", "id": "dummy_keyword_id_2"},
            ]
        }
        mock_get_mute_keyword_list.side_effect = lambda: mock_keyword_dict
        mock_v1.reset_mock()
        with self.assertRaises(ValueError):
            actual = instance.unmute_keyword(keyword)
        mock_v1.assert_not_called()

        mock_keyword_dict = {
            "muted_keywords": [
                {"keyword": "no_hit", "id": "dummy_keyword_id"},
            ]
        }
        mock_get_mute_keyword_list.side_effect = lambda: mock_keyword_dict
        mock_v1.reset_mock()
        with self.assertRaises(ValueError):
            actual = instance.unmute_keyword(keyword)
        mock_v1.assert_not_called()

    def test_mute_user(self):
        mock_v1: MagicMock = self.mock_account.return_value.v1
        mock_v1.side_effect = lambda path, params: "dummy_respone"
        screen_name = "dummy_screen_name"
        path = "mutes/users/create.json"
        payload = {
            "screen_name": screen_name,
        }
        instance = self._get_instance()
        actual = instance.mute_user(screen_name)
        mock_v1.assert_called_once_with(path, payload)
        self.assertEqual("dummy_respone", actual)

    def test_unmute_user(self):
        mock_v1: MagicMock = self.mock_account.return_value.v1
        mock_v1.side_effect = lambda path, params: "dummy_respone"
        screen_name = "dummy_screen_name"
        path = "mutes/users/destroy.json"
        payload = {
            "screen_name": screen_name,
        }
        instance = self._get_instance()
        actual = instance.unmute_user(screen_name)
        mock_v1.assert_called_once_with(path, payload)
        self.assertEqual("dummy_respone", actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
