import contextlib
import datetime
import io
import os
import unittest
from unittest.mock import patch

from create_daily_memo import BEIJING, MemoError, create_memos, get_memo_dates, main


class DateRangeTests(unittest.TestCase):
    def test_requested_range_includes_all_eighteen_dates(self):
        dates = get_memo_dates(start_date="2026-09-04", end_date="2026-09-21")
        self.assertEqual(dates, [f"2026-09-{day:02}" for day in range(4, 22)])

    def test_default_end_is_today_in_beijing(self):
        now = datetime.datetime(2026, 9, 20, 16, tzinfo=datetime.timezone.utc)
        self.assertEqual(
            get_memo_dates(start_date="2026-09-20", now=now),
            ["2026-09-20", "2026-09-21"],
        )

    def test_default_and_single_date_remain_compatible(self):
        now = datetime.datetime(2026, 9, 21, tzinfo=BEIJING)
        self.assertEqual(get_memo_dates(now=now), ["2026-09-21"])
        self.assertEqual(get_memo_dates("2024-02-29", now=now), ["2024-02-29"])

    def test_single_day_range(self):
        self.assertEqual(
            get_memo_dates(start_date="2026-09-04", end_date="2026-09-04"),
            ["2026-09-04"],
        )

    def test_leap_day_and_month_boundary(self):
        self.assertEqual(
            get_memo_dates(start_date="2024-02-28", end_date="2024-03-01"),
            ["2024-02-28", "2024-02-29", "2024-03-01"],
        )

    def test_year_boundary(self):
        self.assertEqual(
            get_memo_dates(start_date="2025-12-31", end_date="2026-01-01"),
            ["2025-12-31", "2026-01-01"],
        )

    def test_invalid_or_conflicting_inputs_fail_before_writes(self):
        selections = [
            {"start_date": "2026-02-29", "end_date": "2026-03-01"},
            {"start_date": "2026-09-04", "end_date": "bad"},
            {"start_date": "2026-09-21", "end_date": "2026-09-04"},
            {"end_date": "2026-09-21"},
            {"date_str": "2026-09-21", "start_date": "2026-09-04"},
            {"date_str": "2026-09-21", "end_date": "2026-09-21"},
        ]
        with patch("create_daily_memo.create_memo") as create:
            for selection in selections:
                with self.subTest(selection=selection), self.assertRaises(MemoError):
                    create_memos(**selection)
            create.assert_not_called()

    def test_upper_date_boundary_does_not_overflow(self):
        self.assertEqual(
            get_memo_dates(start_date="9999-12-31", end_date="9999-12-31"),
            ["9999-12-31"],
        )


class BatchExecutionTests(unittest.TestCase):
    def setUp(self):
        self.output = io.StringIO()
        stdout = contextlib.redirect_stdout(self.output)
        stdout.__enter__()
        self.addCleanup(stdout.__exit__, None, None, None)

    @patch("create_daily_memo.time.sleep")
    @patch("create_daily_memo.create_memo")
    def test_writes_are_ordered_and_paced(self, create, sleep):
        count = create_memos(start_date="2026-09-04", end_date="2026-09-06")
        self.assertEqual(count, 3)
        self.assertEqual([call.args[0] for call in create.call_args_list],
                         ["2026-09-04", "2026-09-05", "2026-09-06"])
        self.assertTrue(all(call.kwargs == {"dry_run": False} for call in create.call_args_list))
        self.assertEqual(sleep.call_count, 2)
        self.assertIn("3/3", self.output.getvalue())

    @patch("create_daily_memo.time.sleep")
    @patch("create_daily_memo.requests.put")
    def test_real_preview_is_offline_without_credentials(self, request, sleep):
        with patch.dict(os.environ, {}, clear=True):
            count = create_memos(start_date="2026-09-04", end_date="2026-09-21", dry_run=True)
        self.assertEqual(count, 18)
        request.assert_not_called()
        sleep.assert_not_called()
        self.assertEqual(self.output.getvalue().count("预览：#日记"), 18)
        self.assertIn("18/18", self.output.getvalue())

    @patch("create_daily_memo.time.sleep")
    @patch("create_daily_memo.create_memo", side_effect=[None, MemoError("HTTP 429"), None])
    def test_failure_stops_later_dates_and_reports_progress(self, create, sleep):
        with self.assertRaisesRegex(MemoError, r"2026-09-05 失败；已完成 1/3 天"):
            create_memos(start_date="2026-09-04", end_date="2026-09-06")
        self.assertEqual(create.call_count, 2)
        sleep.assert_called_once_with(1)
        self.assertNotIn("批量创建完成", self.output.getvalue())

    @patch("create_daily_memo.load_dotenv")
    @patch("create_daily_memo.time.sleep")
    @patch("create_daily_memo.create_memo")
    def test_cli_range_creates_each_selected_date(self, create, sleep, dotenv):
        self.assertEqual(main(["--start-date", "2026-09-04", "--end-date", "2026-09-05"]), 0)
        self.assertEqual([call.args[0] for call in create.call_args_list],
                         ["2026-09-04", "2026-09-05"])

    @patch("create_daily_memo.load_dotenv")
    @patch("create_daily_memo.create_memo")
    def test_cli_conflicting_input_exits_nonzero(self, create, dotenv):
        with contextlib.redirect_stderr(io.StringIO()):
            result = main(["--date", "2026-09-21", "--start-date", "2026-09-04"])
        self.assertEqual(result, 1)
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
