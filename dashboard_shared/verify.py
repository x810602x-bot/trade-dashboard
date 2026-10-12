"""Published numbers must match supplied NAV, trades and strategy rules."""
import json
from pathlib import Path
import re
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard_shared.performance import measure
from dashboard_shared.strategies import CONFIGS

for page,config in CONFIGS.items():
    source=ROOT/('watch2_native' if page=='watch2' else 'strategy2026_native')
    payload=json.loads((source/'data.json').read_text(encoding='utf-8'))
    stats=json.loads((source/'native_stats.json').read_text(encoding='utf-8'))
    nav=pd.read_csv(source/'nav.csv',index_col=0,parse_dates=True).iloc[:,0]
    trades=pd.read_csv(source/'trades.csv',dtype={'stock_id':str})
    perf,years,months,_=measure(nav,trades,stats if config['has_native_report'] else None)
    assert all(abs(perf[k]-v)<1e-10 if isinstance(v,(float,int)) else perf[k]==v for k,v in payload['performance'].items())
    assert years.keys()==payload['yearly_returns'].keys() and months.keys()==payload['monthly_returns'].keys()
    assert all(abs(years[k]-v)<1e-10 for k,v in payload['yearly_returns'].items())
    assert all(abs(months[k]-v)<1e-10 for k,v in payload['monthly_returns'].items())
    html=(ROOT/'_site'/page/'index.html').read_text(encoding='utf-8')
    embedded=json.loads(re.search(r'<script id="strategy-data" type="application/json">(.*?)</script>',html,re.S).group(1))
    assert embedded=={**payload,'config':config}
    assert '../assets/allocation.js?' in html and '../assets/dashboard.js?' in html
    assert '__PAYLOAD_JSON__' not in html
    for path in source.iterdir():
        if path.suffix in ('.json','.csv') or path.name=='report.html':
            assert path.read_bytes()==(ROOT/'_site'/page/path.name).read_bytes()
print('PASS: both pages share rendering/allocation and every statistic matches its NAV and transaction source.')
