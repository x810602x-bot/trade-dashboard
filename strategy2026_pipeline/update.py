"""Preserve the 200-yuan strategy; replace only performance measurement."""
import argparse
from datetime import datetime,time
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
import pandas as pd
import finlab
from finlab import data

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard_shared.performance import clean,save,measure

STATE=ROOT/'strategy2026_pipeline/selections.json'
TZ=ZoneInfo('Asia/Taipei')
DATASETS=['price:收盤價','price:開盤價','price:成交股數','etl:adj_close','etl:adj_open',
    'monthly_revenue:當月營收','monthly_revenue:去年同月增減(%)','company_basic_info']


def legacy_loader(directory):
    def get(name):
        frame=pd.read_pickle(directory/f'{name}.pickle')
        if 'date' in frame.columns:
            frame=frame.set_index('date')
            frame.index=pd.to_datetime(frame.index)
        frame.columns=frame.columns.astype(str).str.split(' ').str[0]
        return frame.T.groupby(level=0).first().T if frame.columns.duplicated().any() else frame
    return get


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


def run(legacy_dir=None,cached=False):
    now=datetime.now(TZ)
    if legacy_dir:
        get=legacy_loader(Path(legacy_dir))
        info=pd.read_pickle(Path(legacy_dir)/'company_basic_info.pickle')
    else:
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
    if not legacy_dir:
        append_selection(state,get,info,now,end)
    assert all(state['selections'][k]==v for k,v in before['selections'].items())
    holdings={pd.Timestamp(k):pd.Series(v['yoy']).loc[v['picks']] for k,v in state['selections'].items() if pd.Timestamp(k)<=end}
    days=close.index.sort_values()
    rebalances={day:days[days>day][0] for day in holdings if len(days[days>day])}
    scope={'gat':get,'holdings':holdings,'rebalance_map':rebalances,'trading_days':days,'close':close,
        'FEE_BUY':.001425,'FEE_SELL':.001425,'TAX_SELL':.003,'MAX_POSITIONS':10,'pd':pd}
    source=ROOT/'strategy2026_pipeline/source/original_engine.py'
    exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),scope)
    raw_nav=pd.Series(scope['nav_series'])
    # Retain the pre-trade account value so the first entry's costs count too.
    initial_day=days[days<raw_nav.index[0]][-1]
    nav=pd.concat([pd.Series([1.],index=[initial_day]),raw_nav])
    names=dict(zip(info.stock_id.astype(str),info['公司簡稱']))
    raw_open=get('price#開盤價')
    def price(frame,day,sid):
        return frame.at[day,sid] if day in frame.index and sid in frame.columns else None
    records=[]
    for t in scope['trade_log']:
        sid=t['stock_id']
        records.append({'stock_id':sid,'name':names.get(sid,''),'entry_date':t['buy_date'],'exit_date':t['sell_date'],
          'entry_sig_date':None,'exit_sig_date':None,'return':t['return'],'position':.1,
          'trade_price@entry_date':price(raw_open,t['buy_date'],sid),'trade_price@exit_date':price(raw_open,t['sell_date'],sid),
          'close':price(raw,end,sid)})
    for sid,pos in scope['positions'].items():
        cur=price(close,end,sid)
        records.append({'stock_id':sid,'name':names.get(sid,''),'entry_date':pos['buy_date'],'exit_date':pd.NaT,
          'entry_sig_date':None,'exit_sig_date':None,'return':cur/pos['buy_price']-1 if pd.notna(cur) else None,'position':.1,
          'trade_price@entry_date':price(raw_open,pos['buy_date'],sid),'trade_price@exit_date':None,'close':price(raw,end,sid)})
    trades=pd.DataFrame(records)
    perf,years,months,stats=measure(nav,trades)
    selected=max(holdings);latest=state['selections'][str(selected.date())]
    pending=[{'stock_id':s,'name':names.get(s,''),'entry_date':None,'exit_date':None,'entry_sig_date':selected,
        'return':None,'position':.1,'close':price(raw,end,s)} for s in latest['picks'] if selected==end and s not in scope['positions']]
    closed=trades[trades.exit_date.notna()]
    payload={'schema_version':1,'strategy_version':state['strategy_version'],'date':str(end.date()),'generated_at':now.isoformat(),
      'start':str(nav.index[0].date()),'selection_date':str(selected.date()),'performance':perf,'yearly_returns':years,'monthly_returns':months,
      'holdings':trades[trades.exit_date.isna()].to_dict('records'),'pending':pending,
      'recent_sells':closed[closed.exit_date==closed.exit_date.max()].to_dict('records'),'latest_selection':latest,
      'allocation_prices':{s:{'close':price(raw,end,s),'name':names.get(s,'')} for s in set(latest['picks'])|set(scope['positions'])},
      'limitations':['沿用原版交易引擎與手續費；獲利未自動再投入，CAGR 只是以完整淨值換算的年化增長率。',
          '歷史名單含原版重算及鎖定結果，不代表當時均有保存；2026 年 8 月的兩次換股照原紀錄保留。',
          '保留原版缺價回退方式，未額外模擬滑價、未成交或整張限制。'],
      'metric_sources':{'cagr':'finlab.backtest.metrics_from_nav','sharpe':'FinLab daily Sharpe; rf=0.02',
          'max_drawdown':'finlab.backtest.metrics_from_nav','yearly_monthly':'finlab.ffn_core.PerformanceStats.return_table',
          'trades':'preserved original transaction engine'}}
    out=ROOT/'strategy2026_native';out.mkdir(exist_ok=True)
    save(out/'data.json',payload);save(out/'native_stats.json',stats)
    nav.to_csv(out/'nav.csv',encoding='utf-8-sig');trades.to_csv(out/'trades.csv',index=False,encoding='utf-8-sig')
    save(out/'validation.json',{'strategy_rules_unchanged':True,'performance_backend':'finlab.metrics_from_nav',
        'finlab_sim_used':False,'fees_unchanged':True,'historical_decisions_unchanged':True,'data_date':str(end.date())})
    if legacy_dir:
        expected=pd.read_csv(ROOT/'.runtime/dashboard_migration/original_nav.csv',index_col=0,parse_dates=True).iloc[:,0]
        assert expected.index.equals(raw_nav.index) and (abs(expected-raw_nav)<1e-12).all()
        original_trades=pd.read_pickle(ROOT/'.runtime/dashboard_migration/original_trades.pkl')
        assert len(closed)==len(original_trades)
        assert [(x['stock_id'],x['buy_date'],x['sell_date'],x['return']) for x in scope['trade_log']]==[(r.stock_id,r.buy_date,r.sell_date,r['return']) for _,r in original_trades.iterrows()]
        save(ROOT/'.runtime/dashboard_migration/parity.json',{'all_1437_transactions_equal':True,'daily_nav_equal':True,'first_entry_costs_included':True})
    else:
        save(STATE,state)
    print(json.dumps({'date':payload['date'],'performance':perf},ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--legacy-dir');parser.add_argument('--cached',action='store_true')
    args=parser.parse_args();run(args.legacy_dir,args.cached)
