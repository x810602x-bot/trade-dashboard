"""Preserve 200-yuan selections and use the same reinvestment model as watch2."""
import argparse
from datetime import datetime,time
import importlib.metadata
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
import pandas as pd
import finlab
from finlab import data
from finlab.backtest import sim

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard_shared.performance import clean,save,measure
from dashboard_shared.positions import position_from_state
from dashboard_shared.strategies import CONFIGS

STATE=ROOT/'strategy2026_pipeline/selections.json'
TZ=ZoneInfo('Asia/Taipei')
DATASETS=['price:收盤價','price:開盤價','price:成交股數','etl:adj_close','etl:adj_open',
    'monthly_revenue:當月營收','monthly_revenue:去年同月增減(%)','company_basic_info',
    'benchmark_return:發行量加權股價報酬指數','etl:market_value','etl:is_flagged_stock',
    'security_categories','delisting_announcements']


def append_selection(state,get,info,now,end):
    """The original current-month revenue gate, never replace a saved decision."""
    close,raw=get('etl#adj_close'),get('price#收盤價')
    days=close.index
    period=end.to_period('M')
    eligible=days[(days.to_period('M')==period)&(days.day>=10)]
    if period<pd.Period(state['live_from'][:7]) or any(pd.Timestamp(k).to_period('M')==period for k in state['selections']) or not len(eligible):
        return
    # Only publish an actual pre-open decision, never backfill after trading.
    calendar=data.get_calendar('tw')
    if now<datetime.combine(end.date(),time(22),TZ):
        return
    if now>=calendar.open_at(calendar.next_session(end.date())):
        raise RuntimeError('Latest price date is stale; refusing to create a decision after its next open.')
    rev,yoy=get('monthly_revenue#當月營收'),get('monthly_revenue#去年同月增減(%)')
    financial=set(info.loc[info['產業類別'].isin(['金融保險業','金融業']),'stock_id'].astype(str))
    rows=rev.index[rev.index<=end]
    if not len(rows):
        return
    row=rows[-1];offset=rev.index.get_loc(row)
    prior=rev.index[offset-1] if offset else row
    prior_keys=[k for k in state['selections'] if pd.Timestamp(k)<end]
    held=state['selections'][max(prior_keys)]['picks'] if prior_keys else []
    missing=[s for s in held if s in rev.columns and pd.isna(rev.loc[row,s]) and pd.notna(rev.loc[prior,s])]
    cols=rev.columns.difference(financial)
    ready=not missing and rev.loc[row,cols].notna().sum()>=rev.loc[prior,cols].notna().sum()*.995
    if not ready and len(eligible)-1<5:
        return
    # All monthly rolling windows are computed before native FinLab alignment.
    avg=rev.rolling(2).mean()
    pool=close.columns.intersection(rev.columns).difference(financial)
    cond=(avg>=avg.rolling(12).max()) & ((close>=close.rolling(200).max()).rolling(5).sum()>=2)
    cond=cond & (get('price#成交股數').rolling(5).mean()>500000) & (raw<=200)
    selected=cond.loc[end,pool]
    candidates=selected.index[selected.fillna(False)]
    score=yoy.loc[yoy.index[yoy.index<=end][-1],yoy.columns.intersection(candidates)]
    score=score[score>0].dropna().sort_values(ascending=False).head(10)
    if score.empty:
        return  # Original rule: no qualifying list means no rebalance.
    state['selections'][str(end.date())]={'picks':list(score.index),'yoy':score.to_dict(),
        'source':'original_revenue_gate','recorded_at':now.isoformat(),'forced':not ready}


def run(cached=False):
    assert importlib.metadata.version('finlab')=='2.2.10'
    now=datetime.now(TZ)
    data.set_storage(data.FileStorage(path=str(ROOT/'.runtime/cache'),use_cache=True))
    finlab.login()
    if not cached:
        for name in DATASETS:
            data.get(name,force_download=True)
    data.use_local_data_only=True
    get=lambda name:data.get(name.replace('#',':'))
    info=data.get('company_basic_info')
    close=get('etl#adj_close')
    raw=get('price#收盤價')
    end=min(close.index[-1],raw.index[-1])
    if end.date()==now.date() and now.time()<time(16):
        end=close.index[close.index<end][-1]
    original_get=get
    get=lambda name:original_get(name).loc[:end]
    close=get('etl#adj_close');raw=get('price#收盤價')
    before=json.loads(STATE.read_text(encoding='utf-8'))
    state=json.loads(json.dumps(before))
    append_selection(state,get,info,now,end)
    assert all(state['selections'][k]==v for k,v in before['selections'].items())
    config=CONFIGS['2026'];allocation=config['allocation']
    position=position_from_state(state,close.columns,end)
    report=sim(position,resample=position.index,position_limit=allocation['weight'],
        fee_ratio=allocation['fee_buy'],tax_ratio=allocation['tax_sell'],stop_loss=None,trade_at_price='open',
        end_date=str(end.date()),upload=False,notification_enable=False,name='每月換股／200元／獲利再投入')
    stats=report.get_stats(riskfree_rate=.02)
    trades=report.get_trades().copy()
    nav=report.daily_creturn.copy()
    assert str(nav.index[-1].date())==str(end.date())
    perf,years,months,_=measure(nav,trades,stats)
    closed=trades.loc[trades.entry_date.notna() & trades.exit_date.notna()]
    holding=trades.loc[trades.entry_date.notna() & trades.exit_date.isna()]
    pending=trades.loc[trades.entry_date.isna() & trades.entry_sig_date.notna()]
    columns=['stock_id','name','entry_date','exit_date','entry_sig_date','exit_sig_date',
        'return','position','trade_price@entry_date','trade_price@exit_date']
    def rows(frame):
        result=[]
        for row in frame[columns].to_dict('records'):
            sid=str(row['stock_id'])
            row['close']=raw.loc[end,sid] if sid in raw.columns else None
            result.append(row)
        return result
    selected=position.index[-1]
    latest={**state['selections'][str(selected.date())],
        'execution_date':str(data.get_calendar('tw').next_session(selected.date()))}
    payload={'schema_version':1,'strategy_version':config['strategy_version'],'date':str(end.date()),'generated_at':now.isoformat(),
      'start':str(position.index[0].date()),'selection_date':str(selected.date()),'performance':perf,'yearly_returns':years,'monthly_returns':months,
      'holdings':rows(holding),'pending':rows(pending),
      'recent_sells':rows(closed.loc[closed.exit_date==closed.exit_date.max()]),'latest_selection':latest,
      'allocation_prices':{s:{'close':raw.loc[end,s],'name':''} for s in latest['picks']},
      'limitations':['沿用 200 元版選股名單、日期與手續費；全段歷史改以換股時總資產配置，獲利再投入。',
          '歷史名單含原版重算及鎖定結果，不代表當時均有保存；2026 年 8 月的兩次換股照原紀錄保留。',
          '與 600 元版同用 FinLab 開盤價模擬及缺價處理，未額外模擬滑價、未成交或整張限制。'],
      'metric_sources':{'cagr':'report.get_stats().cagr','sharpe':'report.get_stats().daily_sharpe; riskfree_rate=0.02',
          'max_drawdown':'report.get_stats().max_drawdown','win_rate':'report.get_stats().win_ratio',
          'yearly_monthly':'report.get_stats().return_table','trades':'report.get_trades()'}}
    out=ROOT/'strategy2026_native';out.mkdir(exist_ok=True)
    save(out/'data.json',payload);save(out/'native_stats.json',stats)
    nav.to_csv(out/'nav.csv',encoding='utf-8-sig');trades.to_csv(out/'trades.csv',index=False,encoding='utf-8-sig')
    report.to_html(str(out/'report.html'))
    save(out/'validation.json',{'strategy_version':config['strategy_version'],'selection_rules_unchanged':True,
        'allocation_mode':'rebalance','finlab_sim_used':True,'native_finlab_version':importlib.metadata.version('finlab'),
        'fees_unchanged':True,'historical_decisions_unchanged':True,'all_cards_from_same_report':True,'data_date':str(end.date())})
    save(STATE,state)
    print(json.dumps({'date':payload['date'],'performance':perf},ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cached',action='store_true')
    args=parser.parse_args();run(args.cached)
