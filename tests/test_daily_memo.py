import contextlib
import datetime
import io
import os
import unittest
from unittest.mock import Mock, patch

import requests

from create_daily_memo import (
    BEIJING,
    CREATE_MEMO_URL,
    MemoError,
    build_memo_payload,
    create_memo,
    get_timestamp_for_date,
    main,
)
from flomo_sign import get_sign


class DateAndSignatureTests(unittest.TestCase):
    def test_midnight_is_in_beijing(self):
        actual = datetime.datetime.fromtimestamp(
            get_timestamp_for_date("2026-09-21"), datetime.timezone.utc
        )
        self.assertEqual(actual.isoformat(), "2026-09-20T16:00:00+00:00")

    def test_valid_leap_day(self):
        result = datetime.datetime.fromtimestamp(
            get_timestamp_for_date("2024-02-29"), BEIJING
        )
        self.assertEqual(result.isoformat(), "2024-02-29T00:00:00+08:00")

    def test_invalid_dates_are_rejected(self):
        for value in ("2026-02-29", "2026-13-01", "2026-9-1", "20260921", "bad", '$(id)', "2026-09-21\n"):
            with self.subTest(value=value), self.assertRaises(MemoError):
                get_timestamp_for_date(value)

    def test_today_switches_at_beijing_midnight(self):
        for hour, expected in ((15, "2026-09-20"), (16, "2026-09-21")):
            now = datetime.datetime(2026, 9, 20, hour, tzinfo=datetime.timezone.utc)
            date, params = build_memo_payload(now=now)
            self.assertEqual(date, expected)
            self.assertEqual(params["content"], f"<p>#日记 {expected}</p>")
            self.assertEqual(params["timestamp"], int(now.timestamp()))

    def test_explicit_date_preserves_current_request_timestamp(self):
        now = datetime.datetime(2026, 9, 21, 12, tzinfo=BEIJING)
        date, params = build_memo_payload("2024-02-29", now=now)
        self.assertEqual(date, "2024-02-29")
        self.assertEqual(params["created_at"], get_timestamp_for_date(date))
        self.assertEqual(params["timestamp"], int(now.timestamp()))
        self.assertEqual(params["api_key"], "flomo_web")
        self.assertEqual(params["file_ids"], [])

    def test_source_protocol_signature_vector(self):
        params = {
            "limit": 200, "latest_updated_at": 0, "tz": "8:0",
            "timestamp": 1720075310, "api_key": "flomo_web",
            "app_version": "4.0", "platform": "web", "webp": "1",
        }
        self.assertEqual(get_sign(params), "d4498ffd175f8e29ddb0bb79c1f5b157")
        self.assertEqual(get_sign(dict(reversed(list(params.items())))), get_sign(params))

    def test_source_protocol_list_and_empty_value_vector(self):
        self.assertEqual(
            get_sign({"b": "", "a": 0, "list": [3, 1, 2], "none": None}),
            "bb11be4b3a7ecc0ad8cefb2d8b90ed88",
        )


class RequestTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {
            "FLOMO_TOKEN": "test-account-token", "FLOMO_DEVICE_ID": "test-device-id",
        }, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        request = patch("create_daily_memo.requests.put")
        self.request = request.start()
        self.addCleanup(request.stop)
        self.request.return_value = Mock(status_code=200)
        self.request.return_value.json.return_value = {"code": 0, "data": {"slug": "private-slug"}}
        self.output = io.StringIO()
        stdout = contextlib.redirect_stdout(self.output)
        stdout.__enter__()
        self.addCleanup(stdout.__exit__, None, None, None)

    def test_create_sends_expected_request_once(self):
        create_memo("2026-09-21")
        self.request.assert_called_once()
        args, kwargs = self.request.call_args
        self.assertEqual(args, (CREATE_MEMO_URL,))
        self.assertEqual(kwargs["headers"]["authorization"], "Bearer test-account-token")
        self.assertEqual(kwargs["headers"]["device-id"], "test-device-id")
        self.assertEqual(kwargs["json"]["content"], "<p>#日记 2026-09-21</p>")
        self.assertEqual(kwargs["timeout"], 15)
        self.assertFalse(kwargs["allow_redirects"])
        self.assertIn("成功", self.output.getvalue())
        self.assertNotIn("private-slug", self.output.getvalue())
        self.assertNotIn("test-account-token", self.output.getvalue())

    def test_authorization_alias_takes_precedence(self):
        with patch.dict(os.environ, {"FLOMO_AUTHORIZATION": "Bearer alias-token"}):
            create_memo("2026-09-21")
        self.assertEqual(self.request.call_args.kwargs["headers"]["authorization"], "Bearer alias-token")

    def test_empty_alias_falls_back_to_token(self):
        with patch.dict(os.environ, {"FLOMO_AUTHORIZATION": " "}):
            create_memo("2026-09-21")
        self.assertEqual(self.request.call_args.kwargs["headers"]["authorization"], "Bearer test-account-token")

    def test_missing_credentials_never_send_requests(self):
        for key in ("FLOMO_TOKEN", "FLOMO_DEVICE_ID"):
            with self.subTest(key=key), patch.dict(os.environ, {key: " "}):
                with self.assertRaises(MemoError):
                    create_memo("2026-09-21")
        self.request.assert_not_called()

    def test_preview_needs_no_credentials_or_network(self):
        with patch.dict(os.environ, {}, clear=True):
            create_memo("2026-09-21", dry_run=True)
        self.request.assert_not_called()
        self.assertIn("#日记 2026-09-21", self.output.getvalue())

    def test_empty_bearer_token_never_sends_request(self):
        with patch.dict(os.environ, {"FLOMO_TOKEN": "Bearer "}):
            with self.assertRaises(MemoError):
                create_memo("2026-09-21")
        self.request.assert_not_called()

    def test_invalid_date_never_sends_request(self):
        with self.assertRaises(MemoError):
            create_memo("2026-02-29")
        self.request.assert_not_called()

    def test_http_failure_does_not_log_response_body(self):
        self.request.return_value = Mock(status_code=401, text="secret-response-body")
        with self.assertRaisesRegex(MemoError, "401") as error:
            create_memo("2026-09-21")
        self.assertNotIn("secret-response-body", str(error.exception) + self.output.getvalue())

    def test_business_failure_does_not_log_message(self):
        self.request.return_value.json.return_value = {"code": -10, "message": "secret-response-body"}
        with self.assertRaisesRegex(MemoError, "-10") as error:
            create_memo("2026-09-21")
        self.assertNotIn("secret-response-body", str(error.exception) + self.output.getvalue())

    def test_malformed_response_fails_cleanly(self):
        for result in (None, [], {}, {"code": "0"}, {"code": False}):
            with self.subTest(result=result):
                self.request.return_value.json.return_value = result
                with self.assertRaises(MemoError):
                    create_memo("2026-09-21")

    def test_non_json_response_fails_cleanly(self):
        self.request.return_value.json.side_effect = ValueError("private response")
        with self.assertRaisesRegex(MemoError, "JSON"):
            create_memo("2026-09-21")

    def test_timeout_is_sanitized_and_not_retried(self):
        self.request.side_effect = requests.Timeout("private request metadata")
        with self.assertRaises(MemoError) as error:
            create_memo("2026-09-21")
        self.request.assert_called_once()
        self.assertNotIn("private request metadata", str(error.exception) + self.output.getvalue())

    def test_cli_failure_returns_nonzero(self):
        stderr = io.StringIO()
        with patch("create_daily_memo.load_dotenv"), contextlib.redirect_stderr(stderr):
            code = main(["--date", "2026-02-29"])
        self.assertEqual(code, 1)
        self.assertIn("错误", stderr.getvalue())
        self.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
