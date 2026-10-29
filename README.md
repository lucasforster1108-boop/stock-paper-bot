# stock-paper-bot

A US-stock **paper-trading** bot for strategy validation: **pure Python standard library, single file, virtual money only — no broker account, no orders, no real money.** Market data comes from Yahoo Finance's public chart API.

The built-in strategy is trend + momentum with hard exits. Signals are computed at the close of day T and filled at the open of day T+1, with 0.15 % slippage charged per side.

## Rules

**Buy** (ranked by 20-day relative strength vs SPY, strongest first), when a stock is not held:
- close > 20-day SMA > 50-day SMA
- RSI(14) < 70
- 20-day return beats SPY's 20-day return

**Sell** a held stock when any exit triggers:
- stop loss −7 % · take profit +18 %
- close falls below the 20-day SMA
- held for 20 trading days

**Portfolio**: virtual $1,000, at most 4 positions, ~$330 per slot (capped at 34 % of NAV per fill). A built-in backtest mode replays the same rules over the last ~253 trading days and reports return vs SPY, max drawdown and win rate.

Daily runs report NAV, positions, fills and the next day's plan; the report is printed, appended to `ledger.jsonl`, and — if you configure it — pushed to a Telegram chat. It only sends when something happened, on Fridays, or on the first run.

## Deployment

1. **Configure (optional)**: `cp config.example.json config.json` and adjust the universe/parameters. Without `config.json` the built-in defaults apply. To receive Telegram reports, put your bot token in its own file and set `telegram.bot_token_file` + `telegram.chat_id` in `config.json`; leave them empty and the bot simply prints.
2. **Run**:

   ```bash
   python3 paper.py run        # one daily step (this is what cron calls)
   python3 paper.py backtest   # replay the rules on ~1 year of history
   python3 paper.py status     # dump current state
   ```

   Schedule the daily step after the US close on trading days, e.g. with cron:

   ```cron
   0 7 * * 2-6  cd /opt/stock-paper-bot && /usr/bin/python3 paper.py run >> run.log 2>&1
   ```

   (07:00 in a UTC+8 timezone ≈ after the US close, Tuesday–Saturday.) The runner retries for a while if Yahoo hasn't published the new bar yet, and skips quietly when there is no new trading day.

State is kept in `state.json` and every fill in `ledger.jsonl`, both next to the script.

## Configuration (config.json)

| Key | Description |
| --- | --- |
| `tradable` | The stock universe to scan. |
| `benchmark` | Benchmark symbol for relative strength and reporting (default SPY). |
| `capital` | Virtual starting capital (USD). |
| `max_positions` | Maximum simultaneous positions. |
| `slot_usd` | Target notional per position slot. |
| `slippage` | Slippage charged per side (default 0.15 %). |
| `stop_loss` / `take_profit` | Hard exit thresholds (defaults −7 % / +18 %). |
| `max_hold_days` | Maximum holding period in trading days. |
| `telegram.bot_token_file` | Path to a file containing your Telegram bot token (token never goes into config or code). Empty = no push. |
| `telegram.chat_id` | Chat ID to push daily reports to. Empty = no push. |

## Notes & disclaimer

- This is a **validation tool**, not financial advice: paper results — especially backtests on a hand-picked universe over a favourable period — overstate what live trading would do. Survivorship and selection bias are real; treat any good-looking number as a hypothesis, not evidence.
- Yahoo's chart API is an unofficial public endpoint; it can change or rate-limit without notice.
- Report texts are in Chinese; they are plain string literals and can be replaced freely.

## Custom development

Universe, rules and thresholds are all adjustable. If you need a variant (different strategy, data source, or reporting), a customized or hosted version can be arranged — contact the author.

## License

MIT, see [LICENSE](LICENSE).

---

## 中文版

一个美股**纸面交易（模拟盘）**机器人，用来验证策略：**纯 Python 标准库、单文件、只有虚拟资金——没有券商账户、不下单、不动真钱。**行情取自 Yahoo Finance 的公开 chart 接口。

内置策略是趋势 + 动量，配硬性退出规则。第 T 日收盘出信号、第 T+1 日开盘成交，每边收 0.15 % 滑点。

### 规则

**买入**（未持仓时，按相对 SPY 的 20 日强度排序，强的先买）：
- 收盘价 > 20 日均线 > 50 日均线
- RSI(14) < 70
- 20 日涨幅跑赢 SPY 同期涨幅

**卖出**（持仓触发任意一条即卖）：
- 止损 −7 % · 止盈 +18 %
- 收盘跌破 20 日均线
- 持有满 20 个交易日

**组合**：虚拟本金 $1,000，最多 4 只，单只约 $330（单笔另有不超过净值 34 % 的上限）。内置回测模式：用同一套规则回放最近约 253 个交易日，输出相对 SPY 的收益、最大回撤和胜率。

每日运行时输出净值、持仓、成交和下一交易日计划；报告会打印、记入 `ledger.jsonl`，配置好后还会推送到 Telegram。只有「有动作、或周五、或首次运行」时才推送。

### 部署三步

1. **填配置（可选）**：`cp config.example.json config.json` 改股票池和参数。不建也行，内置默认值与示例一致。想收 Telegram 报告：把 bot token 单独存一个文件，在 `config.json` 里填 `telegram.bot_token_file` 和 `telegram.chat_id`；留空就只打印不推送。
2. **运行**：

   ```bash
   python3 paper.py run        # 每日一步（cron 调的就是这个）
   python3 paper.py backtest   # 用约 1 年历史回放规则
   python3 paper.py status     # 查看当前状态
   ```

   在交易日美股收盘后定时跑，例如 cron：

   ```cron
   0 7 * * 2-6  cd /opt/stock-paper-bot && /usr/bin/python3 paper.py run >> run.log 2>&1
   ```

   （07:00 按 UTC+8 约为美股收盘后，周二到周六。）如果 Yahoo 还没出新 K 线，运行器会重试等待；没有新交易日就安静跳过。

状态保存在同目录的 `state.json`，每笔成交记入 `ledger.jsonl`。

### 配置项说明（config.json）

| 键 | 说明 |
| --- | --- |
| `tradable` | 扫描的股票池。 |
| `benchmark` | 相对强度与对照基准（默认 SPY）。 |
| `capital` | 虚拟起始本金（美元）。 |
| `max_positions` | 最多同时持仓数。 |
| `slot_usd` | 每个仓位的目标名义金额。 |
| `slippage` | 每边滑点（默认 0.15 %）。 |
| `stop_loss` / `take_profit` | 硬退出阈值（默认 −7 % / +18 %）。 |
| `max_hold_days` | 最长持有交易日数。 |
| `telegram.bot_token_file` | 存放 Telegram bot token 的文件路径（token 不写进 config、更不写进代码）。留空 = 不推送。 |
| `telegram.chat_id` | 日报推送目标 chat ID。留空 = 不推送。 |

### 说明与免责

- 这是**验证工具**，不是投资建议：纸面成绩——尤其是在人工挑选的股票池、顺风行情里跑出的回测——会系统性高估实盘表现。幸存者偏差和挑选偏差真实存在；任何好看的数字都只算一个待验证的假设，不算证据。
- Yahoo chart 接口是非官方公开端点，可能随时变更或限流。
- 报告文案为中文，都是普通字符串，可自行替换。

### 定制开发

股票池、规则、阈值都能自己改。如果需要变体（换策略、换数据源、换报表形式），需要定制版或代部署，可联系作者获取付费定制服务。

### License

MIT，见 [LICENSE](LICENSE)。
