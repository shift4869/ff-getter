import json
import sys
import time
import unittest
from contextlib import ExitStack
from datetime import datetime
from logging import WARNING, getLogger
from unittest.mock import call

import requests
from freezegun import freeze_time
from mock import MagicMock, patch
from requests_oauthlib import OAuth1Session

from ffgetter.twitter_api import TwitterAPI, TwitterAPIEndpoint
from ffgetter.value_object.user_id import UserId
from ffgetter.value_object.user_record import Follower, Following
from ffgetter.value_object.user_record_list import FollowerList, FollowingList

logger = getLogger("ffgetter.twitter_api")
logger.setLevel(WARNING)


class TestTwitterAPI(unittest.TestCase):
    def _get_instance(self) -> TwitterAPI:
        dummy_api_key = "dummy_api_key"
        dummy_api_secret = "dummy_api_secret"
        dummy_access_token_key = "dummy_access_token_key"
        dummy_access_token_secret = "dummy_access_token_secret"
        with patch("ffgetter.twitter_api.TwitterAPI.get"):
            instance = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
        return instance

    def test_endpoint(self):
        expect = [
            ("USER_LOOKUP_ME", "https://api.twitter.com/2/users/me"),
            ("FOLLOWING", "https://api.twitter.com/2/users/{}/following"),
            ("FOLLOWERS", "https://api.twitter.com/2/users/{}/followers"),
            ("POST_TWEET", "https://api.twitter.com/2/tweets"),
        ]
        actual = [(item.name, item.value) for item in TwitterAPIEndpoint]
        self.assertEqual(expect, actual)

    def test_init(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI.get"))

            dummy_api_key = "dummy_api_key"
            dummy_api_secret = "dummy_api_secret"
            dummy_access_token_key = "dummy_access_token_key"
            dummy_access_token_secret = "dummy_access_token_secret"

            actual = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
            self.assertEqual(dummy_api_key, actual.api_key)
            self.assertEqual(dummy_api_secret, actual.api_secret)
            self.assertEqual(dummy_access_token_key, actual.access_token_key)
            self.assertEqual(dummy_access_token_secret, actual.access_token_secret)
            self.assertTrue(isinstance(actual.oauth, OAuth1Session))

            with self.assertRaises(TypeError):
                actual = TwitterAPI(None, dummy_api_secret, dummy_access_token_key, dummy_access_token_secret)
            with self.assertRaises(TypeError):
                actual = TwitterAPI(dummy_api_key, None, dummy_access_token_key, dummy_access_token_secret)
            with self.assertRaises(TypeError):
                actual = TwitterAPI(dummy_api_key, dummy_api_secret, None, dummy_access_token_secret)
            with self.assertRaises(TypeError):
                actual = TwitterAPI(dummy_api_key, dummy_api_secret, dummy_access_token_key, None)

    def test_wait(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "debug"))
            mock_sys = stack.enter_context(patch("sys.stdout.flush"))
            mock_sleep = stack.enter_context(patch("time.sleep"))

            twitter = self._get_instance()
            wait_time = 5
            dt_unix = time.mktime(datetime.now().timetuple()) + wait_time
            actual = twitter._wait(dt_unix)
            mock_sys.assert_called()
            mock_sleep.assert_called()

    def test_wait_until_reset(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "debug"))
            mock_wait = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI._wait"))

            dt_format = "%Y-%m-%d %H:%M:%S"
            now_time_str = "2022-10-19 10:00:00"
            mock_freezegun = stack.enter_context(freeze_time(now_time_str))

            twitter = self._get_instance()

            wait_time = 5
            reset_dt_unix = time.mktime(datetime.strptime(now_time_str, dt_format).timetuple()) + wait_time
            dummy_response = MagicMock()
            dummy_response.headers = {
                "x-rate-limit-limit": 75,
                "x-rate-limit-remaining": 70,
                "x-rate-limit-reset": reset_dt_unix,
            }
            actual = twitter._wait_until_reset(dummy_response)
            mock_wait.assert_not_called()

            dummy_response.headers = {
                "x-rate-limit-limit": 75,
                "x-rate-limit-remaining": 0,
                "x-rate-limit-reset": reset_dt_unix,
            }
            actual = twitter._wait_until_reset(dummy_response)
            mock_wait.assert_called_once_with(reset_dt_unix + 3)

            dummy_response.headers = {}
            with self.assertRaises(requests.HTTPError):
                actual = twitter._wait_until_reset(dummy_response)

    def test_request(self):
        with ExitStack() as stack:
            mock_logger = stack.enter_context(patch.object(logger, "warning"))
            mock_oauth_get = stack.enter_context(patch("ffgetter.twitter_api.OAuth1Session.get"))
            mock_oauth_post = stack.enter_context(patch("ffgetter.twitter_api.OAuth1Session.post"))
            mock_oauth_delete = stack.enter_context(patch("ffgetter.twitter_api.OAuth1Session.delete"))
            mock_wait_until_reset = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI._wait_until_reset"))
            mock_wait = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI._wait"))

            endpoint_url = TwitterAPIEndpoint.USER_LOOKUP_ME.value
            dummy_params = {"dummy_params": "dummy_params"}

            r = MagicMock()
            r.text = '{"dummy_response_text": "get_dummy_response_text"}'
            mock_oauth_get.side_effect = lambda endpoint_url, params: r
            mock_oauth_post.side_effect = lambda endpoint_url, json: r
            mock_oauth_delete.side_effect = lambda endpoint_url, params: r

            twitter = self._get_instance()
            expect = json.loads(r.text)
            actual = twitter.request(endpoint_url, dummy_params, "GET")
            self.assertEqual(expect, actual)
            mock_oauth_get.assert_called_once_with(endpoint_url, params=dummy_params)
            mock_oauth_get.reset_mock()

            endpoint_url = TwitterAPIEndpoint.POST_TWEET.value
            r.text = '{"dummy_response_text": "post_dummy_response_text"}'
            expect = json.loads(r.text)
            actual = twitter.request(endpoint_url, dummy_params, "POST")
            self.assertEqual(expect, actual)
            mock_oauth_post.assert_called_once_with(endpoint_url, json=dummy_params)
            mock_oauth_post.reset_mock()

            endpoint_url = TwitterAPIEndpoint.USER_LOOKUP_ME.value
            r.text = '{"dummy_response_text": "get_dummy_response_text"}'
            expect = json.loads(r.text)
            mock_oauth_get.side_effect = [None, None, r]
            actual = twitter.request(endpoint_url, dummy_params, "GET")
            self.assertEqual(expect, actual)
            called = mock_oauth_get.mock_calls
            self.assertEqual(4, len(called))
            self.assertEqual(call(endpoint_url, params=dummy_params), called[1])
            self.assertEqual(call(endpoint_url, params=dummy_params), called[2])
            self.assertEqual(call(endpoint_url, params=dummy_params), called[3])
            mock_oauth_get.reset_mock()

            mock_oauth_get.side_effect = [None, None, None, None, None, r]
            with self.assertRaises(requests.HTTPError):
                actual = twitter.request(endpoint_url, dummy_params, "GET")
            mock_oauth_get.reset_mock()

            with self.assertRaises(ValueError):
                actual = twitter.request(endpoint_url, dummy_params, "invalid_method")

    def test_get(self):
        with ExitStack() as stack:
            mock_request = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI.request"))

            dummy_endpoint_url = "dummy_endpoint_url"
            dummy_params = {"dummy_params": "dummy_params"}

            mock_request.side_effect = lambda endpoint_url, params, method: (endpoint_url, params, method)

            twitter = self._get_instance()
            expect = (dummy_endpoint_url, dummy_params, "GET")
            actual = twitter.get(dummy_endpoint_url, dummy_params)
            self.assertEqual(expect, actual)
            mock_request.assert_called_once_with(endpoint_url=dummy_endpoint_url, params=dummy_params, method="GET")

    def test_post(self):
        with ExitStack() as stack:
            mock_request = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI.request"))

            dummy_endpoint_url = "dummy_endpoint_url"
            dummy_params = {"dummy_params": "dummy_params"}

            mock_request.side_effect = lambda endpoint_url, params, method: (endpoint_url, params, method)

            twitter = self._get_instance()
            expect = (dummy_endpoint_url, dummy_params, "POST")
            actual = twitter.post(dummy_endpoint_url, dummy_params)
            self.assertEqual(expect, actual)
            mock_request.assert_called_once_with(endpoint_url=dummy_endpoint_url, params=dummy_params, method="POST")

    def test_get_user_id(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI.get"))
            user_id = 12345678
            mock_get.return_value = {"data": {"id": str(user_id)}}
            twitter = self._get_instance()
            actual = twitter.get_user_id()
            expect = UserId(user_id)
            self.assertEqual(expect, actual)

            url = TwitterAPIEndpoint.USER_LOOKUP_ME.value
            mock_get.assert_called_once_with(url, params={})
            mock_get.reset_mock()

            mock_get.return_value = {"invalid_dict": "invalid_dict"}
            with self.assertRaises(ValueError):
                actual = twitter.get_user_id()

    def test_get_following(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI.get"))
            user_id = 12345678
            expect_data = [
                {"id": f"{user_id}{i}", "name": f"ユーザー{i}", "username": f"screen_name_{i}"}
                for i in range(5)
            ]
            mock_get.return_value = {
                "data": expect_data
            }
            twitter = self._get_instance()
            actual = twitter.get_following(UserId(user_id))
            expect = FollowingList.create([
                Following.create(
                    data.get("id"),
                    data.get("name"),
                    data.get("username"),
                )
                for data in expect_data
            ])
            self.assertEqual(expect, actual)

            MAX_RESULTS = 1000
            url = TwitterAPIEndpoint.FOLLOWING.value.format(user_id)
            mock_get.assert_called_once_with(url, params={"max_results": MAX_RESULTS})

    def test_get_follower(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI.get"))
            user_id = 12345678
            expect_data = [
                {"id": f"{user_id}{i}", "name": f"ユーザー{i}", "username": f"screen_name_{i}"}
                for i in range(5)
            ]
            mock_get.return_value = {
                "data": expect_data
            }
            twitter = self._get_instance()
            actual = twitter.get_follower(UserId(user_id))
            expect = FollowerList.create([
                Follower.create(
                    data.get("id"),
                    data.get("name"),
                    data.get("username"),
                )
                for data in expect_data
            ])
            self.assertEqual(expect, actual)

            MAX_RESULTS = 1000
            url = TwitterAPIEndpoint.FOLLOWERS.value.format(user_id)
            mock_get.assert_called_once_with(url, params={"max_results": MAX_RESULTS})

    def test_post_tweet(self):
        with ExitStack() as stack:
            mock_post = stack.enter_context(patch("ffgetter.twitter_api.TwitterAPI.post"))
            mock_post.return_value = {"data": "result_ok"}
            tweet_str = "post_tweet_str"
            twitter = self._get_instance()
            actual = twitter.post_tweet(tweet_str)
            expect = {"data": "result_ok"}
            self.assertEqual(expect, actual)

            url = TwitterAPIEndpoint.POST_TWEET.value
            mock_post.assert_called_once_with(url, params={"text": tweet_str})


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
