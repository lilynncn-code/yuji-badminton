# 比赛自动更新

首页、赛事签表和比赛详情每次出现时都会重新读取后台。本机保存上次成功的内容和时间；无网、来源报错或后台保存失败会显示旧内容及提示。首次没有保存内容时显示明确标记的2026年5月历史资料。排名和资讯没有改动。

## 接通来源

目前没有配置可用的官方比赛数据，不能宣称已经接通实时比赛。请取得授权、可从服务器读取的完整 JSON 数据。羽联普通网页不是本功能的输入地址。不同供应方的字段不同，取得地址和样本后如有需要，应先转换成下面的格式。

在后台 `.env` 中填写其中一种：

```dotenv
MATCH_SOURCE_URL=https://授权服务地址/完整比赛.json
MATCH_SOURCE_TOKEN=如果需要则填写授权令牌
# 或使用授权文件；两者都填写时优先文件
MATCH_SOURCE_FILE=/服务器绝对路径/比赛.json
MATCH_SYNC_ENABLED=true
MATCH_SYNC_TIMEOUT=20
```

不要在前端填写账号、令牌或私人来源地址。`MATCH_SOURCE_TOKEN` 通过后台请求的 Authorization Bearer 头发送。公开来源页面须单独填入文件的 `source_url`，后台不会把私人读取地址、文件路径、请求令牌或原始异常发给页面。

## 更新和人工导入

正常后台启动时自动检查，之后每900秒再检查。最近15分钟已有检查则跳过；多个正常后台进程共用一条同步记录，避免重复执行。成功或失败会写入后台日志。停止后台也会停止自动检查。

已有数据库在正常启动时会自动建立新增的 `matches` 和 `match_sync_state` 表，无需清空已有数据。赛事说明使用已有 `events` 表，排名和资讯读取不变。

人工导入（先正常启动后台建立新表）：

```bash
cd backend
.venv/bin/python scripts/sync_matches.py --file '/授权文件的绝对路径/比赛.json'
```

立即检查已经配置的来源：

```bash
.venv/bin/python scripts/sync_matches.py
```

返回 `ok: true` 表示保存完成；失败返回退出码1并保留全部旧比赛。手动导入不会修改后台的定时来源配置。只有授权文件时，可让提供方每次完整替换该文件；未更新的文件不会被描述为新的来源更新时间。

如果服务器希望使用已有的外部定时管理器，可设 `MATCH_SYNC_ENABLED=false` 并参照 `scripts/sync_matches.cron` 每15分钟执行一次。不要同时设置两套自动执行。仓库里的示例文件不会自动安装服务器任务；本次也没有部署远程服务器。

## 完整文件约定

每次输入是一个完整快照，包含希望保留的全部近期赛事和比赛。不能只提供新变化或某一页结果；删除的比赛会从后台消失，明确取消则保留编号并使用 `cancelled`。全空、未读完整、重复编号、错误日期、错误胜者或保存失败都会拒绝替换。

编号应采用来源方永久编号，在所有赛事内唯一，并在重命名、改轮次、改比分后保持不变。编号不能包含 `/`、`?`、`#` 或反斜线，`history-` 开头保留给内置历史资料。双打选手放在同一方名称内，用 ` / ` 分隔。

下面只是格式示例，选手、赛事和比分均为生成的检查内容，不是真实比赛。不要将示例作为正式来源：

```json
{
  "complete": true,
  "source_updated_at": "2026-10-31T10:00:00Z",
  "source_url": "https://example.com/public-results",
  "events": [
    {
      "id": "provider-event-001",
      "name": "检查赛事（临时生成）",
      "start_date": "2026-10-26",
      "end_date": "2026-11-01",
      "status": "ongoing",
      "location": "检查场地",
      "image_url": "",
      "summary": "这是格式示例"
    }
  ],
  "matches": [
    {
      "id": "provider-match-001",
      "event_id": "provider-event-001",
      "discipline": "男单",
      "round": "半决赛",
      "scheduled_at": "2026-10-31T18:00:00+08:00",
      "court": "第一场地",
      "player1": "检查选手甲",
      "player2": "检查选手乙",
      "score1": "21 11",
      "score2": "19 10",
      "score_text": "21-19, 11-10",
      "winner": "",
      "status": "live",
      "image_url": "",
      "image_source": "",
      "replay_url": "",
      "report": "检查内容，不是真实比赛"
    }
  ]
}
```

`source_updated_at` 是提供方的实际更新时间，未知时省略，不能每次读取时伪造。早于上次成功来源时间的快照被拒绝。所有时间按UTC保存和读取，页面按手机所在时区显示。`scheduled_at` 未定时可为 `null`。赛事必须有起止日期。图片、回放、报道和场地可为空，页面会给出相应空内容或本机备用图。单次文件最大10MB，最多200站赛事及10000场比赛。

比赛状态支持 `scheduled`（未开始）、`live`（比赛中）、`finished`（已完赛）、`cancelled`（已取消）、`postponed`（已延期）、`walkover`（退赛）、`retired`（中途退赛）。赛事状态支持 `upcoming`、`ongoing`、`finished`、`cancelled`。胜者只能为空或等于某一方选手名称，取消的比赛不能有胜者。

## 页面读取

- `GET /content/matches`：返回最近5站有比赛的赛事及其全部比赛，按比赛时间倒序、编号排序；赛事选项独立于比赛条数。
- `GET /content/matches?limit=6`：首页最新6场，包含同一批赛事选项。
- `GET /content/matches?event_id=...`：指定赛事的全部比赛。
- `GET /content/matches/{match_id}`：单场详情，不存在时返回404，页面不替换为其他比赛。

`sync` 带最近成功保存时间 `latest_updated_at`、来源更新时间 `source_updated_at`、最近尝试 `last_attempt_at`、是否旧内容 `using_old_data`、失败说明 `last_error` 和公开来源页 `source_url`。来源失败或超过30分钟没有成功检查时标记旧内容。读取地址禁止浏览器保存旧响应，前端也为每次读取带不同标记。

## 检查

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests -p test_matches.py -v
node frontend/scripts/checks/matches.cjs
```

`backend/tests/match_preview_server.py` 只使用临时数据库及生成的检查比赛，可用于独立网页检查，关闭后删除临时数据。它不连接真实官方来源，也不证明安卓、苹果手机实机已通过。
