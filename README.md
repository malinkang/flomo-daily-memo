# flomo-daily-memo

通过 GitHub Actions 每天自动创建一条 flomo 日记：

```text
#日记 2026-09-21
```

默认按北京时间（UTC+8）确定日期，并将笔记创建时间设为当天 00:00。也可以手动指定日期补建笔记。

## 配置 GitHub Actions

1. Fork 本仓库，或在自己的账号下使用本仓库代码。
2. 登录 [flomo 网页版](https://v.flomoapp.com/)，打开浏览器开发者工具的 **Network** 面板，刷新页面，选择发送到 `flomoapp.com/api/` 的请求。
3. 从请求头取出本人账号的 `Authorization` 和 `device-id`。
4. 打开 GitHub 仓库的 **Settings → Secrets and variables → Actions → New repository secret**，添加：

| Secret | 值 |
| --- | --- |
| `FLOMO_TOKEN` | flomo 请求头中的 Authorization；可包含 `Bearer ` 前缀 |
| `FLOMO_DEVICE_ID` | 同一请求的 `device-id` |

也支持用 `FLOMO_AUTHORIZATION` 替代 `FLOMO_TOKEN`；同时配置时优先使用前者。凭证只填入 GitHub Secrets 或本地 `.env`，不要写入代码、Issue 或日志。

5. 在 **Actions** 页面启用工作流。
6. 选择 **Create Daily Flomo Memo → Run workflow**，勾选 `dry_run` 可先预览；取消勾选才会创建笔记。`date` 留空使用北京时间今天，也可以填写 `YYYY-MM-DD`。

定时任务配置为每天 **16:00 UTC（北京时间次日 00:00）**。GitHub 定时任务可能延迟，实际执行时按北京时间当天确定默认日期。未配置 Secrets 时，定时任务会跳过并提示配置。

公开仓库长时间没有活动时，GitHub 可能自动停用定时工作流；可在 Actions 页面重新启用。登录凭证失效后，需要从已登录的 flomo 网页请求重新获取并更新 Secrets。

## 本地使用

需要 Python 3.10 或更新版本。

```bash
git clone https://github.com/malinkang/flomo-daily-memo.git
cd flomo-daily-memo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

填写 `.env` 后运行：

```bash
# 创建今天的日记
python create_daily_memo.py

# 补建指定日期的日记
python create_daily_memo.py --date 2026-09-21

# 只预览内容和日期；无需凭证，不发送网络请求
python create_daily_memo.py --date 2026-09-21 --dry-run
```

## 从已有工作流迁移

在新仓库配置自己的 Secrets；GitHub 不支持读回旧仓库的 Secret 值。切换定时任务前，在旧仓库 Actions 中停用对应工作流，避免两个仓库重复创建。

每次实际运行都会创建一条笔记，重复执行同一天会产生重复内容。发生超时或网络错误时，先到 flomo 确认是否已经创建，再决定是否重试。

## 开发与验证

```bash
python -m py_compile create_daily_memo.py flomo_sign.py
python -m unittest discover -s tests -v
```

测试模拟 API 响应，不需要真实凭证，不会创建笔记。此工具独立于 Notion 和 NotionHub，只依赖 `requests` 和 `python-dotenv`。它使用 flomo 网页端协议，网页接口变化可能需要更新脚本。

## License

[MIT](LICENSE)
