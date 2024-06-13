import shutil
import sys
import unittest
from collections import namedtuple
from pathlib import Path

from mock import PropertyMock, patch

from ff_getter.fetcher.fetcher_base import FetcherBase, FollowerFetcher, FollowingFetcher
from ff_getter.util import FFtype
from ff_getter.value_object.user_record import Follower, Following
from ff_getter.value_object.user_record_list import FollowerList, FollowingList


class TestFetcherBase(unittest.TestCase):
    def setUp(self) -> None:
        cache_path = Path("./tests/ff_getter/fetcher/cache")
        cache_path.mkdir(parents=True, exist_ok=True)
        return super().tearDown()

    def tearDown(self) -> None:
        cache_path = Path("./tests/ff_getter/fetcher/cache")
        cache_path.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(cache_path)
        return super().tearDown()

    def _get_instance(self) -> FetcherBase:
        config = {
            "twitter_api_client": {
                "ct0": "dummy_ct0",
                "auth_token": "dummy_auth_token",
                "target_screen_name": "dummy_target_screen_name",
                "target_id": 0,
            }
        }
        mock_cache_path = self.enterContext(patch("ff_getter.fetcher.fetcher_base.FetcherBase.cache_path"))
        instance = FetcherBase(config, FFtype.following, True)
        mock_cache_path = PropertyMock()
        mock_cache_path.return_value = Path(f"./tests/ff_getter/fetcher/cache/{instance.ff_type.value}/").resolve()
        type(instance).cache_path = mock_cache_path
        return instance

    def test_init(self):
        config = {
            "twitter_api_client": {
                "ct0": "dummy_ct0",
                "auth_token": "dummy_auth_token",
                "target_screen_name": "dummy_target_screen_name",
                "target_id": 0,
            }
        }
        instance = FetcherBase(config, FFtype.following, False)
        self.assertEqual("dummy_ct0", instance.ct0)
        self.assertEqual("dummy_auth_token", instance.auth_token)
        self.assertEqual("dummy_target_screen_name", instance.target_screen_name)
        self.assertEqual(0, instance.target_id)
        self.assertEqual(FFtype.following, instance.ff_type)
        self.assertEqual(False, instance.is_debug)
        self.assertEqual(
            Path("./src/ff_getter/fetcher").resolve() / f"cache/{instance.ff_type.value}/", instance.cache_path
        )

        instance = FetcherBase(config, FFtype.follower, True)
        self.assertEqual(FFtype.follower, instance.ff_type)
        self.assertEqual(True, instance.is_debug)

        with self.assertRaises(TypeError):
            instance = FetcherBase("invalid_argument", FFtype.following, False)
        with self.assertRaises(ValueError):
            instance = FetcherBase({"twitter_api_client": "invalid_config"}, FFtype.following, False)
        with self.assertRaises(ValueError):
            instance = FetcherBase({"twitter_api_client": {}}, FFtype.following, False)

        with self.assertRaises(ValueError):
            instance = FetcherBase(config, "invalid_argument", False)
        with self.assertRaises(ValueError):
            instance = FetcherBase(config, FFtype.following, "invalid_argument")

    def test_fetch_jsons(self):
        mock_logger = self.enterContext(patch("ff_getter.fetcher.fetcher_base.logger"))
        mock_scraper = self.enterContext(patch("ff_getter.fetcher.fetcher_base.Scraper"))

        Params = namedtuple("Params", ["ff_type", "is_debug", "is_error_occur"])

        def pre_run(params: Params, instance: FetcherBase) -> FetcherBase:
            instance.ff_type = params.ff_type
            instance.is_debug = params.is_debug
            instance.cache_path = Path(f"./tests/ff_getter/fetcher/cache/{instance.ff_type.value}/").resolve()
            instance.cache_path.mkdir(parents=True, exist_ok=True)
            if params.is_error_occur:
                (instance.cache_path / "content_cache0.txt").unlink(missing_ok=True)
            else:
                (instance.cache_path / "content_cache0.txt").write_text('{"dummy_json": {}}')

            mock_scraper.reset_mock()
            mock_scraper.return_value.following.side_effect = lambda user_ids: [{"dummy_json": {}}]
            mock_scraper.return_value.followers.side_effect = lambda user_ids: [{"dummy_json": {}}]

            return instance

        def post_run(params: Params, instance: FetcherBase) -> FetcherBase:
            if params.is_debug:
                mock_scraper.return_value.followers.assert_not_called()
                mock_scraper.return_value.following.assert_not_called()
            else:
                if params.ff_type == FFtype.following:
                    mock_scraper.return_value.following.assert_called_once_with([instance.target_id])
                    mock_scraper.return_value.followers.assert_not_called()
                elif params.ff_type == FFtype.follower:
                    mock_scraper.return_value.following.assert_not_called()
                    mock_scraper.return_value.followers.assert_called_once_with([instance.target_id])
            return instance

        params_list = [
            (Params(FFtype.following, False, False), [{"dummy_json": {}}]),
            (Params(FFtype.follower, False, False), [{"dummy_json": {}}]),
            (Params(FFtype.following, True, False), [{"dummy_json": {}}]),
            (Params(FFtype.follower, True, False), [{"dummy_json": {}}]),
            (Params(FFtype.following, True, True), "ValueError"),
            (Params(FFtype.follower, True, True), "ValueError"),
        ]
        for params, expect in params_list:
            instance = self._get_instance()
            instance = pre_run(params, instance)
            if expect == "ValueError":
                with self.assertRaises(ValueError):
                    actual = instance.fetch_jsons()
            else:
                actual = instance.fetch_jsons()
                self.assertEqual(expect, actual)
            post_run(params, instance)

    def test_interpret_json(self):
        instance = self._get_instance()
        result_json = {
            "rest_id": "dummy_rest_id",
            "legacy": {
                "name": "dummy_name",
                "screen_name": "dummy_screen_name",
            },
        }
        json_dict = {
            "content": {
                "itemContent": {"user_results": {"result": result_json}},
            },
        }
        actual = instance.interpret_json(json_dict)
        expect = {
            "id_str": "dummy_rest_id",
            "name": "dummy_name",
            "screen_name": "dummy_screen_name",
        }
        self.assertEqual(expect, actual)

        actual = instance.interpret_json({})
        self.assertEqual({}, actual)
        actual = instance.interpret_json("invalid_argument")
        self.assertEqual({}, actual)

    def test_to_convert(self):
        instance = self._get_instance()
        result_json = {
            "rest_id": 0,
            "legacy": {
                "name": "dummy_name",
                "screen_name": "dummy_screen_name",
            },
        }
        json_dict = {
            "entries": [
                {
                    "content": {
                        "itemContent": {"user_results": {"result": result_json}},
                    }
                }
            ]
        }
        instance.ff_type = FFtype.following
        actual = instance.to_convert([json_dict])
        expect = FollowingList.create(Following.create(0, "dummy_name", "dummy_screen_name"))
        self.assertEqual(expect, actual)

        instance.ff_type = FFtype.follower
        actual = instance.to_convert([json_dict])
        expect = FollowerList.create(Follower.create(0, "dummy_name", "dummy_screen_name"))
        self.assertEqual(expect, actual)

        instance.ff_type = FFtype.following
        actual = instance.to_convert([{"entries": [{}]}])
        self.assertEqual([], actual)
        actual = instance.to_convert(["invalid_argument"])
        self.assertEqual([], actual)
        actual = instance.to_convert("invalid_argument")
        self.assertEqual([], actual)

    def test_fetch(self):
        mock_fetch_jsons = self.enterContext(patch("ff_getter.fetcher.fetcher_base.FetcherBase.fetch_jsons"))
        mock_to_convert = self.enterContext(patch("ff_getter.fetcher.fetcher_base.FetcherBase.to_convert"))
        instance = self._get_instance()
        actual = instance.fetch()
        mock_fetch_jsons.assert_called_once_with()
        mock_to_convert.assert_called_once_with(mock_fetch_jsons.return_value)
        self.assertEqual(mock_to_convert.return_value, actual)

    def test_fetcher(self):
        config = {
            "twitter_api_client": {
                "ct0": "dummy_ct0",
                "auth_token": "dummy_auth_token",
                "target_screen_name": "dummy_target_screen_name",
                "target_id": 0,
            }
        }
        instance = FollowingFetcher(config)
        self.assertEqual(FFtype.following, instance.ff_type)
        instance = FollowerFetcher(config)
        self.assertEqual(FFtype.follower, instance.ff_type)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
