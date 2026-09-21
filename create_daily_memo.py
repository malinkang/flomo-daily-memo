"""Create a daily diary memo in flomo without a Notion dependency."""

import argparse
import datetime
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

from flomo_sign import get_sign

BEIJING = datetime.timezone(datetime.timedelta(hours=8))
CREATE_MEMO_URL = "https://flomoapp.com/api/v1/memo"


class MemoError(Exception):
    """An error that is safe to print in a public Actions log."""


def get_timestamp_for_date(date_str):
    """Convert an exact YYYY-MM-DD date to midnight in UTC+8."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        raise MemoError("日期格式必须是 YYYY-MM-DD。")
    try:
        date = datetime.date.fromisoformat(date_str)
    except ValueError:
        raise MemoError("日期无效，请检查年月日。") from None
    return int(datetime.datetime.combine(date, datetime.time(), BEIJING).timestamp())


def get_memo_dates(date_str=None, *, start_date=None, end_date=None, now=None):
    """Validate the whole selection before writing and return inclusive dates."""
    if date_str and (start_date or end_date):
        raise MemoError("date 不能与 start_date 或 end_date 同时使用。")
    if end_date and not start_date:
        raise MemoError("使用 end_date 时必须提供 start_date。")
    today = (now or datetime.datetime.now(BEIJING)).astimezone(BEIJING).date().isoformat()
    first = start_date or date_str or today
    last = (end_date or today) if start_date else first
    get_timestamp_for_date(first)
    get_timestamp_for_date(last)
    start = datetime.date.fromisoformat(first)
    end = datetime.date.fromisoformat(last)
    if start > end:
        raise MemoError("开始日期不能晚于结束日期。")
    return [(start + datetime.timedelta(days=offset)).isoformat()
            for offset in range((end - start).days + 1)]


def build_memo_payload(date_str=None, *, now=None):
    now = now or datetime.datetime.now(BEIJING)
    memo_date = date_str if date_str else now.astimezone(BEIJING).date().isoformat()
    params = {
        "content": f"<p>#日记 {memo_date}</p>",
        "created_at": get_timestamp_for_date(memo_date),
        "source": "web",
        "memo_from": "human",
        "file_ids": [],
        "tz": "8:0",
        "timestamp": int(now.timestamp()),
        "api_key": "flomo_web",  # Public web client identifier, not an account token.
        "app_version": "4.0",
        "platform": "web",
        "webp": "1",
    }
    params["sign"] = get_sign(params)
    return memo_date, params


def create_memo(date_str=None, *, dry_run=False):
    memo_date, params = build_memo_payload(date_str)
    if dry_run:
        print(f"预览：#日记 {memo_date}")
        print(f"创建时间：{memo_date} 00:00:00 +08:00；未发送请求。")
        return

    authorization = (
        os.getenv("FLOMO_AUTHORIZATION", "").strip()
        or os.getenv("FLOMO_TOKEN", "").strip()
    )
    device_id = os.getenv("FLOMO_DEVICE_ID", "").strip()
    if not authorization:
        raise MemoError("缺少 FLOMO_TOKEN（或 FLOMO_AUTHORIZATION）。")
    if not device_id:
        raise MemoError("缺少 FLOMO_DEVICE_ID，请使用本人 flomo 请求中的 device-id。")
    if authorization.lower() == "bearer":
        raise MemoError("FLOMO_TOKEN 的 Bearer token 不能为空。")
    if not authorization.lower().startswith("bearer "):
        authorization = f"Bearer {authorization}"
    if not authorization[7:].strip():
        raise MemoError("FLOMO_TOKEN 的 Bearer token 不能为空。")

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "authorization": authorization,
        "content-type": "application/json",
        "device-id": device_id,
        "origin": "https://v.flomoapp.com",
        "priority": "u=1, i",
        "referer": "https://v.flomoapp.com/",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
    }
    print(f"正在创建每日笔记：{memo_date}")
    try:
        response = requests.put(
            CREATE_MEMO_URL,
            headers=headers,
            json=params,
            timeout=15,
            allow_redirects=False,
        )
    except requests.RequestException:
        raise MemoError("flomo 请求失败，请检查网络；确认笔记是否已创建后再重试。") from None

    if response.status_code != 200:
        raise MemoError(f"flomo HTTP 请求失败：{response.status_code}。")
    try:
        result = response.json()
    except ValueError:
        raise MemoError("flomo 返回了无效的 JSON 响应。") from None
    if not isinstance(result, dict) or type(result.get("code")) is not int:
        raise MemoError("flomo 返回了无法识别的响应。")
    if result["code"] != 0:
        raise MemoError(f"flomo 创建失败，错误码：{result['code']}；请检查登录凭证。")
    print(f"成功！已创建每日笔记：{memo_date}")


def create_memos(date_str=None, *, start_date=None, end_date=None, dry_run=False):
    dates = get_memo_dates(date_str, start_date=start_date, end_date=end_date)
    operation = "预览" if dry_run else "创建"
    print(f"计划{operation} {len(dates)} 天：{dates[0]} 至 {dates[-1]}", flush=True)
    for index, memo_date in enumerate(dates):
        if index and not dry_run:
            time.sleep(1)
        try:
            create_memo(memo_date, dry_run=dry_run)
        except MemoError as error:
            raise MemoError(
                f"{memo_date} 失败；已完成 {index}/{len(dates)} 天。{error} "
                "后续日期尚未执行。先确认失败日期是否已创建，再从该日期或下一天继续。"
            ) from None
        print(f"进度：{index + 1}/{len(dates)}", flush=True)
    print(f"批量{operation}完成：{len(dates)}/{len(dates)} 天。", flush=True)
    return len(dates)


def main(argv=None):
    parser = argparse.ArgumentParser(description="创建 flomo 每日笔记")
    parser.add_argument("--date", help="指定日期 YYYY-MM-DD；默认北京时间今天")
    parser.add_argument("--start-date", help="开始日期 YYYY-MM-DD，与 --date 互斥")
    parser.add_argument("--end-date", help="结束日期 YYYY-MM-DD（包含当天）；默认北京时间今天")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不需要凭证或网络")
    args = parser.parse_args(argv)
    load_dotenv()
    try:
        create_memos(
            args.date,
            start_date=args.start_date,
            end_date=args.end_date,
            dry_run=args.dry_run,
        )
    except MemoError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
