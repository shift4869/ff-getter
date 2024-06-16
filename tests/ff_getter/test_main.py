import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ff_getter.main import main


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_main(self):
        mock_argparse = self.enterContext(patch("ff_getter.main.argparse.ArgumentParser"))
        mock_logger = self.enterContext(patch("ff_getter.main.logger"))
        mock_core = self.enterContext(patch("ff_getter.main.Core"))
        main()
        mock_core.assert_called_once_with(mock_argparse.return_value)
        mock_core.reset_mock()

        prevent_multiple_run_path = Path("./src/ff_getter/prevent_multiple_run")
        prevent_multiple_run_path.touch()
        main()
        mock_core.assert_not_called()
        mock_core.reset_mock()

        mock_core.side_effect = ValueError
        main()

        mock_argparse.return_value.add_argument.side_effect = ValueError
        with self.assertRaises(SystemExit):
            main()
        mock_argparse.reset_mock()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
