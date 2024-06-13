import sys
import unittest

from following_syncer.user import User


class TestUser(unittest.TestCase):
    def test_init(self):
        instance = User("12345678", "test_user🎉", "test_user")
        self.assertEqual("12345678", instance.rest_id)
        self.assertEqual("test_user🎉", instance.name)
        self.assertEqual("test_user", instance.screen_name)
        self.assertFalse(instance.protected)
        repr_str = "rest_id=12345678, name=test_user🎉, screen_name=test_user, protected=False"
        self.assertEqual(repr_str, repr(instance))

        with self.assertRaises(ValueError):
            instance = User(-1, "test_user🎉", "test_user")
        with self.assertRaises(ValueError):
            instance = User("12345678", -1, "test_user")
        with self.assertRaises(ValueError):
            instance = User("12345678", "test_user🎉", -1)
        with self.assertRaises(ValueError):
            instance = User("12345678", "test_user🎉", "test_user", "invalid_argument")

    def test_to_dict(self):
        instance = User("12345678", "test_user🎉", "test_user")
        self.assertEqual(
            {
                "rest_id": instance.rest_id,
                "name": instance.name,
                "screen_name": instance.screen_name,
            },
            instance.to_dict(),
        )


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
