# stock-paper-bot

A paper-trading bot for a US-stock trend+momentum strategy. I wrote it because the backtest looked great and I didn't trust it — this runs the same rules forward, on virtual money, one real trading day at a time. No broker account, no orders, no real money. Yahoo Finance's public chart API for data, stdlib only, one file.

## The rules

Signals are computed at the close of day T and filled at the open of day T+1, with 0.15 % slippage charged per side.

Buy candidates (not currently held), ranked by 20-day relative strength vs SPY, strongest first:

- close > 20-day SMA > 50-day SMA
- RSI(14) < 70
- 20-day return beats SPY's 20-day return

Sell a held stock when any of these triggers:

- −7 % stop loss or +18 % take profit
- close drops below the 20-day SMA
- held for 20 trading days

Portfolio: virtual $1,000, at most 4 positions, about $330 a slot (and no single fill over 34 % of NAV).

## About that backtest

`python3 paper.py backtest` replays the rules over roughly the last 253 trading days. On my universe it printed +68 % vs SPY +14 %, max drawdown −20 %, win rate 44 % over 86 closed trades.

Don't take that number seriously. The stock universe was picked with hindsight, and the sample year happened to be a semiconductor bull run — of course a momentum strategy looks brilliant on it. That's the whole point of this bot: the backtest is a hypothesis, the forward paper record is the test. I gave it a 4-week window before drawing any conclusion, and the real-money conversation only starts after that, if at all.

## Running it

```bash
python3 paper.py run        # one daily step (this is what cron calls)
python3 paper.py backtest   # replay on ~1 year of history
python3 paper.py status     # dump current state
```

I run it from cron after the US close, Tuesday to Saturday in my timezone:

```cron
0 7 * * 2-6  cd /opt/stock-paper-bot && /usr/bin/python3 paper.py run >> run.log 2>&1
```

If Yahoo hasn't published the new bar yet, the runner retries for a while instead of crashing; on non-trading days it just skips. Reports print NAV, positions, fills and tomorrow's plan, and are appended to `ledger.jsonl`. It only pushes to Telegram when something actually happened, on Fridays, or on the first run (set `telegram.bot_token_file` + `telegram.chat_id` in config; leave empty and it just prints). State lives in `state.json` next to the script.

## Config

`cp config.example.json config.json` — without one, built-in defaults apply.

| Key | What it does |
| --- | --- |
| `tradable` | The stock universe to scan (the example file has a generic mega-cap list; put your own in) |
| `benchmark` | Relative-strength benchmark (default SPY) |
| `capital` | Virtual starting capital |
| `max_positions` / `slot_usd` | Portfolio shape |
| `slippage` | Per-side slippage (default 0.15 %) |
| `stop_loss` / `take_profit` | Hard exits (−7 % / +18 %) |
| `max_hold_days` | Max holding period in trading days |
| `telegram.*` | Optional report push; token stays in its own file |

Yahoo's chart endpoint is unofficial and can change or rate-limit whenever it feels like it. Report texts are Chinese literals. This is a validation tool, not financial advice — see the backtest paragraph above before quoting any number from it.

MIT license, see LICENSE.

---

## 中文版

美股趋势+动量策略的纸面机器人。写它的原因就是回测太好看了、我不信——所以让同一套规则用虚拟资金、按真实交易日一天一天往前跑。没有券商账户、不下单、不动真钱。行情用 Yahoo Finance 的公开 chart 接口，纯标准库，单文件。

### 规则

第 T 日收盘出信号、T+1 日开盘成交，每边扣 0.15 % 滑点。

买入候选（未持仓的），按相对 SPY 的 20 日强度排序，强的先买：

- 收盘价 > 20 日均线 > 50 日均线
- RSI(14) < 70
- 20 日涨幅跑赢 SPY 同期

卖出（持仓触发任意一条）：

- 止损 −7 % 或止盈 +18 %
- 收盘跌破 20 日均线
- 持有满 20 个交易日

组合：虚拟本金 $1,000，最多 4 只，单只约 $330，单笔不超过净值的 34 %。

### 关于那个回测

`python3 paper.py backtest` 用同一套规则回放最近约 253 个交易日。在我的股票池上它打出 +68 %、同期 SPY +14 %、最大回撤 −20 %、86 笔平仓胜率 44 %。

这个数字别当真。股票池是按今天的眼光事后挑的，样本期又正好赶上半导体牛年，动量策略在这种数据上不好看才怪。这正是这个机器人存在的意义：回测只是假设，往前跑的纸面记录才是检验。我给它定了 4 周的验证期，结论出来之前不谈真钱。

### 跑法

```bash
python3 paper.py run        # 每日一步（cron 调这个）
python3 paper.py backtest   # 约 1 年历史回放
python3 paper.py status     # 看当前状态
```

我这边是 cron 在美股收盘后跑（我的时区是周二到周六早上 7 点）：

```cron
0 7 * * 2-6  cd /opt/stock-paper-bot && /usr/bin/python3 paper.py run >> run.log 2>&1
```

Yahoo 还没出新 K 线时它会重试等一会儿，不会直接崩；非交易日安静跳过。日报输出净值、持仓、成交和明日计划，记入 `ledger.jsonl`；只有真有动作、或者周五、或者首次运行时才推 Telegram（config 里填 `telegram.bot_token_file` 和 `telegram.chat_id`，留空就只打印）。状态在同目录 `state.json`。

配置 `cp config.example.json config.json`，不建就用内置默认值。键就那些：`tradable` 股票池（示例文件里是通用大盘股名单，换成你自己的）、`benchmark` 基准、`capital` 本金、`max_positions`/`slot_usd` 仓位形状、`slippage` 滑点、`stop_loss`/`take_profit` 硬退出、`max_hold_days` 最长持有、`telegram.*` 可选推送（token 单独放文件里）。

Yahoo 的 chart 接口是非官方端点，随时可能改版或限流。报告文案是中文字符串。它是验证工具，不是投资建议——引用任何数字之前先看上面回测那段。

MIT，见 LICENSE。
