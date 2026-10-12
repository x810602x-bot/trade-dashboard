"""One performance definition for native reports and preserved external NAV."""
import json
import math
from datetime import datetime
import numpy as np
import pandas as pd
from finlab.backtest import metrics_from_nav
from finlab.ffn_core import PerformanceStats


def clean(value):
    if value is pd.NaT or value is None:
        return None
    if isinstance(value, dict):
        return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (pd.Timestamp,datetime)):
        return value.isoformat()
    if isinstance(value,(np.integer,np.floating)):
        value=value.item()
    return None if isinstance(value,float) and not math.isfinite(value) else value


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(clean(value),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def measure(nav,trades,native_stats=None):
    """Measure supplied net NAV; never change orders, sizing or the engine."""
    metric=metrics_from_nav(nav)
    if native_stats is not None:
        stats=dict(native_stats)
    else:
        native=PerformanceStats(nav,rf=.02)
        stats=native.stats.to_dict()
        stats['return_table']=native.return_table.to_dict(orient='index')
    core={'cagr':float(metric.annual_return()),'daily_sharpe':float(metric.sharpe_ratio(riskfree_rate=.02)),
          'max_drawdown':float(metric.max_drawdown())}
    assert all(abs(stats[k]-v)<1e-10 for k,v in core.items())
    closed=trades.loc[trades.entry_date.notna() & trades.exit_date.notna()]
    valid=closed['return'].dropna()
    # Preserve FinLab's own closed-trade win ratio for native Report inputs.
    win=stats['win_ratio'] if native_stats is not None else (float((valid>0).mean()) if len(valid) else None)
    perf={'cagr':stats['cagr'],'sharpe':stats['daily_sharpe'],'max_drawdown':stats['max_drawdown'],
          'win_rate':win,'closed_trades':len(closed),'valid_closed_trades':len(valid),
          'avg_return':valid.mean(),'max_gain':valid.max(),'max_loss':valid.min(),
          'missing_return_trades':len(closed)-len(valid)}
    years,months={},{}
    labels=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    for year,row in stats['return_table'].items():
        years[str(year)]=row['YTD']
        for month,label in enumerate(labels,1):
            if pd.Timestamp(int(year),month,1)<=nav.index[-1]:
                months[f'{int(year):04d}-{month:02d}']=row[label]
    return clean(perf),clean(years),clean(months),clean(stats)
