"""One FinLab report supplies every watch2 performance and trade field."""
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo
import argparse
import hashlib
import importlib.metadata
import json
import sys
import pandas as pd
import finlab
from finlab import data, FinlabDataFrame
from finlab.backtest import sim

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard_shared.performance import clean, save, measure
STATE = ROOT/'watch2_pipeline/selections.json'
VERSION = 'watch2-fixed10-v1'
START = '2008-03-10'
TZ = ZoneInfo('Asia/Taipei')
DATASETS = [
    'price:收盤價', 'price:開盤價', 'price:成交股數', 'price:成交金額',
    'etl:adj_close', 'etl:adj_open', 'monthly_revenue:當月營收',
    'monthly_revenue:去年同月增減(%)', 'company_basic_info',
    'benchmark_return:發行量加權股價報酬指數', 'etl:market_value',
    'etl:is_flagged_stock', 'security_categories', 'delisting_announcements',
]


def first_signal_day(calendar, year, month):
    tenth = datetime(year, month, 10).date()
    return tenth if calendar.is_session(tenth) else calendar.next_session(tenth)


def append_selection(state, close, raw, now):
    """Never reconstruct missed live decisions with later information."""
    calendar = data.get_calendar('tw')
    signal_day = first_signal_day(calendar, now.year, now.month)
    signal = pd.Timestamp(signal_day)
    key = str(signal_day)
    for earlier in pd.period_range(state['live_from'][:7], str(signal_day)[:7], freq='M'):
        required = first_signal_day(calendar, earlier.year, earlier.month)
        deadline = calendar.open_at(calendar.next_session(required))
        if now >= deadline and str(required) not in state['selections']:
            raise RuntimeError(f'Missed frozen selection for {required}; refusing to invent an earlier trade.')
    if key in state['selections'] or now.date() < signal_day:
        return
    if now < datetime.combine(signal_day, time(22), TZ):
        return
    if now >= calendar.open_at(calendar.next_session(signal_day)):
        raise RuntimeError('The planned trading open has passed; late historical selection is forbidden.')
    if signal not in close.index:
        raise RuntimeError('Signal-day closing prices are not yet available; keep the previous published page.')
    rev = data.get('monthly_revenue:當月營收').loc[:signal]
    yoy = data.get('monthly_revenue:去年同月增減(%)').loc[:signal]
    if len(rev) == 0 or rev.index[-1].to_period('M') != signal.to_period('M'):
        raise RuntimeError('Current revenue table is unavailable; do not reuse the previous month as current revenue.')
    info = data.get('company_basic_info')
    financial = set(info.loc[info['產業類別'].isin(['金融保險業','金融業']), 'stock_id'].astype(str))
    pool = close.columns.intersection(rev.columns).difference(financial)
    c, r, y = close.loc[:signal,pool], rev[pool], yoy[pool]
    amount = data.get('price:成交金額').loc[:signal,pool]
    mean = r.rolling(2,min_periods=2).mean()
    eligible = ((mean >= mean.rolling(12,min_periods=12).max())
        & ((c >= c.rolling(200,min_periods=200).max()).rolling(5,min_periods=5).sum() >= 2)
        & (raw.loc[:signal,pool] <= 600) & (y > 0)
        & (amount.rolling(5,min_periods=5).mean() > 30000000))
    score = y * eligible
    chosen = score[score > 0].is_largest(10).loc[signal]
    picks = list(chosen.index[chosen])
    assert len(picks) <= 10 and not (set(picks) & financial)
    state['selections'][key] = {'picks':picks, 'source':'frozen_before_next_open',
        'recorded_at':now.isoformat(), 'execution_date':str(calendar.next_session(signal_day)),
        'inputs_sha256':hashlib.sha256(pd.util.hash_pandas_object(score.loc[signal]).values.tobytes()).hexdigest()}


def position_from_state(state, columns, end):
    records = {day:{sid:.1 for sid in row['picks']} for day,row in state['selections'].items() if day <= str(end.date())}
    # Only construct saved decision rows. Financial input alignment remains native.
    # Preserve empty selections too: they explicitly rebalance the account to cash.
    frame = pd.DataFrame(0., index=pd.to_datetime(sorted(records)), columns=columns)
    for day, weights in records.items():
        if weights:
            frame.loc[pd.Timestamp(day), list(weights)] = .1
    assert len(frame) == len(records)
    assert frame.index.to_period('M').is_unique
    assert frame.gt(0).sum(axis=1).max() <= 10
    return FinlabDataFrame(frame)


def run(reference=False):
    assert importlib.metadata.version('finlab') == '2.2.10'
    cache = ROOT/'.runtime'/('reference_cache' if reference else 'cache')
    cache.mkdir(parents=True,exist_ok=True)
    data.set_storage(data.FileStorage(path=str(cache),use_cache=True))
    finlab.login()
    if not reference:
        for dataset in DATASETS:
            data.get(dataset, force_download=True)
    data.use_local_data_only = True
    raw = data.get('price:收盤價')
    close = data.get('etl:adj_close')
    now = datetime.now(TZ)
    end = pd.Timestamp('2026-09-10') if reference else min(raw.index[-1],close.index[-1])
    if not reference and end.date() == now.date() and now.time() < time(16):
        end = raw.index[raw.index < end][-1]
    before = json.loads(STATE.read_text(encoding='utf-8'))
    state = json.loads(json.dumps(before))
    assert state['strategy_version'] == VERSION
    if not reference:
        append_selection(state, close, raw, now)
    assert all(state['selections'][k] == v for k,v in before['selections'].items())
    position = position_from_state(state, close.columns, end)
    report = sim(position, resample=position.index, position_limit=.1,
        fee_ratio=.000475, tax_ratio=.003, stop_loss=None, trade_at_price='open',
        end_date=str(end.date()), upload=False, notification_enable=False,
        name='每月換股／固定日期／最多10檔／3000萬')
    # Capture each public API once before rendering; never recalculate the
    # website's former fixed-initial-capital profit statistics.
    stats = report.get_stats(riskfree_rate=.02)
    trades = report.get_trades().copy()
    nav = report.daily_creturn.copy()
    assert str(nav.index[-1].date()) == str(end.date())
    if reference:
        expected = {'cagr':.3401941656346643,'daily_sharpe':1.26335788772093,'max_drawdown':-.305252992763152}
        assert all(abs(stats[k]-v)<1e-10 for k,v in expected.items()), {k:stats[k] for k in expected}
    out = ROOT/'.runtime/reference_result' if reference else ROOT/'watch2_native'
    out.mkdir(parents=True,exist_ok=True)
    save(out/'native_stats.json', stats)
    trades.to_csv(out/'trades.csv',index=False,encoding='utf-8-sig')
    nav.to_csv(out/'nav.csv',encoding='utf-8-sig')
    closed = trades.loc[trades.entry_date.notna() & trades.exit_date.notna()]
    pending = trades.loc[trades.entry_date.isna() & trades.entry_sig_date.notna()]
    holding = trades.loc[trades.entry_date.notna() & trades.exit_date.isna()]
    last_exit = closed.exit_date.max()
    recent_sells = closed.loc[closed.exit_date == last_exit]
    columns = ['stock_id','name','entry_date','exit_date','entry_sig_date','exit_sig_date',
               'return','position','trade_price@entry_date','trade_price@exit_date']
    def rows(frame):
        result = []
        for row in frame[columns].to_dict('records'):
            sid = str(row['stock_id'])
            row['close'] = raw.loc[end,sid] if sid in raw.columns else None
            result.append(row)
        return result
    selected_day = position.index[-1]
    performance, year_rows, month_rows, _ = measure(nav,trades,stats)
    payload = {
        'schema_version':1, 'strategy_version':VERSION, 'date':str(end.date()),
        'generated_at':now.isoformat(), 'start':START, 'selection_date':str(selected_day.date()),
        'performance':performance,
        'yearly_returns':year_rows, 'monthly_returns':month_rows,
        'holdings':rows(holding), 'pending':rows(pending), 'recent_sells':rows(recent_sells),
        'latest_selection':state['selections'][str(selected_day.date())],
        'allocation_prices':{str(s):{'close':raw.loc[end,s],'name':''} for s in position.columns
            if s in state['selections'][str(selected_day.date())]['picks']},
        'limitations':['歷史名單沿用已核對的研究回測；2026/10/12起保存當次決策，不回改名單。',
                       '回測以開盤價模擬，未額外計入滑價；缺價交易請見完整報表。'],
        'metric_sources':{'cagr':'report.get_stats().cagr','sharpe':'report.get_stats().daily_sharpe; riskfree_rate=0.02',
            'max_drawdown':'report.get_stats().max_drawdown','win_rate':'report.get_stats().win_ratio',
            'trade_cards':'report.get_trades(); closed rows; average/max/min omit missing returns',
            'yearly_monthly':'report.get_stats().return_table'},
    }
    save(out/'data.json',payload)
    report.to_html(str(out/'report.html'))
    save(out/'validation.json',{'strategy_version':VERSION,'native_finlab_version':importlib.metadata.version('finlab'),
        'historical_decisions_unchanged':True,'selection_months':len(position),
        'reference_metrics_matched':True if reference else None,
        'all_cards_from_same_report':True,'data_date':str(end.date())})
    if not reference:
        save(STATE,state)
    print(json.dumps({'mode':'reference' if reference else 'latest','date':str(end.date()),
        'performance':clean(payload['performance'])},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference',action='store_true')
    run(parser.parse_args().reference)
