#!/usr/bin/env python3
"""US stock paper-trading bot (validation only, no real money).
Rules: trend+momentum entries, hard exits. Signals at close T, fills at open T+1, 0.15% slippage/side."""
import json, os, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_F = os.path.join(BASE, 'state.json')
LEDGER_F = os.path.join(BASE, 'ledger.jsonl')

DEFAULT_CONFIG = {
    'tradable': ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AVGO'],
    'benchmark': 'SPY',
    'capital': 1000.0,
    'max_positions': 4,
    'slot_usd': 330.0,
    'slippage': 0.0015,
    'stop_loss': -0.07,
    'take_profit': 0.18,
    'max_hold_days': 20,
    'telegram': {'bot_token_file': '', 'chat_id': ''},
}

def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    path = os.path.join(BASE, 'config.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg

CFG = load_config()
TRADABLE = list(CFG['tradable'])
BENCH = CFG['benchmark']
CAPITAL = float(CFG['capital'])
MAX_POS = int(CFG['max_positions'])
SLOT = float(CFG['slot_usd'])
SLIP = float(CFG['slippage'])
STOP_LOSS = float(CFG['stop_loss'])
TAKE_PROFIT = float(CFG['take_profit'])
MAX_HOLD = int(CFG['max_hold_days'])
TG_CHAT = str((CFG.get('telegram') or {}).get('chat_id') or '')
NY = ZoneInfo('America/New_York')

def fetch(sym, rng='2y'):
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval=1d'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read())
    res = d['chart']['result'][0]
    ts = res['timestamp']
    q = res['indicators']['quote'][0]
    bars = []
    for i, t in enumerate(ts):
        if q['close'][i] is None or q['open'][i] is None:
            continue
        bars.append({'date': datetime.fromtimestamp(t, NY).strftime('%Y-%m-%d'),
                     'open': float(q['open'][i]), 'close': float(q['close'][i])})
    if ts:
        last_date = datetime.fromtimestamp(ts[-1], NY).strftime('%Y-%m-%d')
        if (not bars or bars[-1]['date'] != last_date) and q['open'][-1] is not None:
            mp = res['meta'].get('regularMarketPrice')
            if mp:
                bars.append({'date': last_date, 'open': float(q['open'][-1]), 'close': float(mp)})
    return bars

def sma(vals, n, i):
    if i + 1 < n: return None
    return sum(vals[i - n + 1:i + 1]) / n

def rsi(closes, i, n=14):
    if i < n: return None
    gains = losses = 0.0
    for j in range(i - n + 1, i + 1):
        ch = closes[j] - closes[j - 1]
        if ch > 0: gains += ch
        else: losses -= ch
    if losses == 0: return 100.0
    rs = gains / losses
    return 100 - 100 / (1 + rs)

def prep(bars_by):
    out = {}
    for s, bars in bars_by.items():
        out[s] = {'dates': [b['date'] for b in bars], 'open': [b['open'] for b in bars],
                  'close': [b['close'] for b in bars], 'by_date': {b['date']: b for b in bars}}
    return out

def signals_at(P, spy, i, held):
    """Return (buy_candidates ranked, sell_reasons dict) using data up to index i of master calendar."""
    date = spy['dates'][i]
    out_buys, out_sells = [], {}
    spy_c = spy['close']
    if i < 50: return out_buys, out_sells
    spy_ret20 = spy_c[i] / spy_c[i - 20] - 1
    for s in TRADABLE:
        d = P.get(s)
        if not d or date not in d['by_date']: continue
        idx = d['dates'].index(date)
        if idx < 50: continue
        c = d['close']
        price = c[idx]
        s20, s50 = sma(c, 20, idx), sma(c, 50, idx)
        if s20 is None or s50 is None: continue
        r = rsi(c, idx)
        rs20 = price / c[idx - 20] - 1 - spy_ret20
        if s in held:
            pnl = price / held[s]['entry_price'] - 1
            hold_days = idx - held[s]['entry_idx']
            reason = None
            if pnl <= STOP_LOSS: reason = f'止损（{pnl*100:.1f}%）'
            elif pnl >= TAKE_PROFIT: reason = f'止盈（+{pnl*100:.1f}%）'
            elif price < s20: reason = '跌破20日线'
            elif hold_days >= MAX_HOLD: reason = f'持有满{MAX_HOLD}个交易日'
            if reason: out_sells[s] = reason
        else:
            if price > s20 > s50 and r is not None and r < 70 and rs20 > 0:
                out_buys.append((rs20, s))
    out_buys.sort(reverse=True)
    return [s for _, s in out_buys], out_sells

def tg(text):
    try:
        if not TG_CHAT:
            return
        tok_file = (CFG.get('telegram') or {}).get('bot_token_file') or ''
        tok = open(tok_file).read().strip()
        data = urllib.parse.urlencode({'chat_id': TG_CHAT, 'text': text}).encode()
        req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendMessage', data=data)
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:
        print('tg fail:', e, file=sys.stderr)
import urllib.parse

def load_state():
    if os.path.exists(STATE_F):
        return json.load(open(STATE_F))
    return {'cash': CAPITAL, 'positions': {}, 'pending': [], 'last_bar_date': None, 'nav_history': []}

def save_state(st):
    json.dump(st, open(STATE_F, 'w'), ensure_ascii=False, indent=1)

def ledger(ev):
    with open(LEDGER_F, 'a') as f:
        f.write(json.dumps(ev, ensure_ascii=False) + '\n')

def backtest():
    syms = TRADABLE + [BENCH]
    P = prep({s: fetch(s, '2y') for s in syms})
    spy = P[BENCH]
    dates = spy['dates']
    start = len(dates) - 253
    cash, pos = CAPITAL, {}
    navs, trades = [], []
    pending = []
    for i in range(start, len(dates)):
        date = dates[i]
        # fills at open
        for od in pending:
            s = od['sym']; d = P[s]
            if date not in d['by_date']: continue
            px = d['by_date'][date]['open']
            if od['side'] == 'buy':
                target = min(SLOT, cash, 0.34 * (cash + sum(pos[x]['shares'] * P[x]['by_date'][date]['close'] for x in pos if date in P[x]['by_date'])))
                shares = int(target // px)
                if shares >= 1 and len(pos) < MAX_POS:
                    cost = shares * px * (1 + SLIP)
                    if cost <= cash:
                        cash -= cost
                        pos[s] = {'shares': shares, 'entry_price': px * (1 + SLIP), 'entry_idx': d['dates'].index(date), 'entry_date': date}
                        trades.append({'side': 'buy', 'sym': s, 'date': date, 'px': px, 'shares': shares})
            else:
                if s in pos:
                    proceeds = pos[s]['shares'] * px * (1 - SLIP)
                    pnl = px * (1 - SLIP) / pos[s]['entry_price'] - 1
                    cash += proceeds
                    trades.append({'side': 'sell', 'sym': s, 'date': date, 'px': px, 'shares': pos[s]['shares'], 'pnl': pnl, 'reason': od.get('reason', '')})
                    del pos[s]
        pending = []
        nav = cash + sum(pos[s]['shares'] * P[s]['by_date'][date]['close'] for s in pos if date in P[s]['by_date'])
        navs.append((date, nav))
        buys, sells = signals_at(P, spy, i, pos)
        for s, rsn in sells.items(): pending.append({'side': 'sell', 'sym': s, 'reason': rsn})
        slots = MAX_POS - len(pos) - sum(1 for o in pending if o['side'] == 'buy')
        for s in buys[:max(0, slots)]: pending.append({'side': 'buy', 'sym': s})
    final = navs[-1][1]
    spy_ret = spy['close'][-1] / spy['close'][start] - 1
    peak, mdd = -1, 0.0
    for _, n in navs:
        peak = max(peak, n); mdd = min(mdd, n / peak - 1)
    closed = [t for t in trades if t['side'] == 'sell']
    wins = sum(1 for t in closed if t['pnl'] > 0)
    print(f"回测区间 {dates[start]} → {dates[-1]}")
    print(f"策略收益: {(final/CAPITAL-1)*100:.1f}%  (期末 ${final:.0f}) | SPY同期: {spy_ret*100:.1f}%")
    print(f"最大回撤: {mdd*100:.1f}% | 卖出 {len(closed)} 笔, 胜率 {wins}/{len(closed)}" if closed else "无卖出")
    print('在持仓:', {s: p['shares'] for s, p in pos.items()})
    return {'ret': final / CAPITAL - 1, 'spy': spy_ret, 'mdd': mdd, 'closed': len(closed), 'wins': wins, 'final': final}

def run_daily():
    st = load_state()
    syms = TRADABLE + [BENCH]
    for attempt in range(4):
        probe = fetch(BENCH, '6mo')
        probed = probe[-1]['date']
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] attempt {attempt + 1}: SPY latest bar {probed} vs last_bar_date {st['last_bar_date']}", flush=True)
        if probed != st['last_bar_date']:
            break
        if attempt < 3:
            time.sleep(240)
    else:
        print('no new bar after retries, skip'); return
    P = prep({s: fetch(s, '6mo') for s in syms})
    spy = P[BENCH]
    latest = spy['dates'][-1]
    i = len(spy['dates']) - 1
    events = []
    for od in st['pending']:
        s = od['sym']; d = P[s]
        if latest not in d['by_date']: continue
        px = d['by_date'][latest]['open']
        if od['side'] == 'buy':
            nav_now = st['cash'] + sum(st['positions'][x]['shares'] * P[x]['by_date'][latest]['close'] for x in st['positions'] if latest in P[x]['by_date'])
            target = min(SLOT, st['cash'], 0.34 * nav_now)
            shares = int(target // px)
            if shares >= 1 and len(st['positions']) < MAX_POS:
                cost = shares * px * (1 + SLIP)
                if cost <= st['cash']:
                    st['cash'] -= cost
                    st['positions'][s] = {'shares': shares, 'entry_price': px * (1 + SLIP), 'entry_idx': d['dates'].index(latest), 'entry_date': latest}
                    ev = f"买入 {s} {shares}股 @ ${px:.2f}"
                    events.append(ev); ledger({'date': latest, 'side': 'buy', 'sym': s, 'px': px, 'shares': shares})
            else:
                events.append(f"买入 {s} 未执行（单股价格过高或仓位已满）")
        else:
            if s in st['positions']:
                sh = st['positions'][s]['shares']
                proceeds = sh * px * (1 - SLIP)
                pnl = px * (1 - SLIP) / st['positions'][s]['entry_price'] - 1
                st['cash'] += proceeds
                ev = f"卖出 {s} {sh}股 @ ${px:.2f}（{od.get('reason','')}，盈亏 {pnl*100:+.1f}%）"
                events.append(ev); ledger({'date': latest, 'side': 'sell', 'sym': s, 'px': px, 'shares': sh, 'pnl': pnl, 'reason': od.get('reason', '')})
                del st['positions'][s]
    st['pending'] = []
    nav = st['cash'] + sum(st['positions'][s]['shares'] * P[s]['by_date'][latest]['close'] for s in st['positions'] if latest in P[s]['by_date'])
    st['nav_history'].append({'date': latest, 'nav': round(nav, 2)})
    buys, sells = signals_at(P, spy, i, st['positions'])
    for s, rsn in sells.items(): st['pending'].append({'side': 'sell', 'sym': s, 'reason': rsn})
    slots = MAX_POS - len(st['positions'])
    for s in buys[:max(0, slots)]: st['pending'].append({'side': 'buy', 'sym': s})
    st['last_bar_date'] = latest
    save_state(st)
    pos_txt = '、'.join(f"{s}×{p['shares']}" for s, p in st['positions'].items()) or '空仓'
    plan = '、'.join(('买' if o['side'] == 'buy' else '卖') + o['sym'] for o in st['pending']) or '无'
    msg = (f"📊 美股纸面盘 {latest}\n净值 ${nav:.0f}（{(nav/CAPITAL-1)*100:+.1f}%）| 现金 ${st['cash']:.0f}\n"
           f"持仓：{pos_txt}\n今日成交：{'；'.join(events) if events else '无'}\n下一交易日计划：{plan}")
    print(msg)
    is_friday = datetime.strptime(latest, '%Y-%m-%d').weekday() == 4
    if events or st['pending'] or is_friday or len(st['nav_history']) == 1:
        tg(msg)

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if cmd == 'backtest': backtest()
    elif cmd == 'run': run_daily()
    elif cmd == 'status':
        st = load_state()
        print(json.dumps(st, ensure_ascii=False, indent=1)[:1200])
