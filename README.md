# stock-paper-bot

English | [简体中文](README_zh.md)

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
