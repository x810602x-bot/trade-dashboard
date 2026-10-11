"""Check the published payload against the exact exported native report."""
from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
source = ROOT/'watch2_native'
d = json.loads((source/'data.json').read_text(encoding='utf-8'))
s = json.loads((source/'native_stats.json').read_text(encoding='utf-8'))
t = pd.read_csv(source/'trades.csv',dtype={'stock_id':str})
c = t.loc[t.entry_date.notna() & t.exit_date.notna()]
v = c['return'].dropna()
p = d['performance']
assert d['strategy_version'] == 'watch2-fixed10-v1'
assert abs(p['cagr']-s['cagr']) < 1e-12
assert abs(p['sharpe']-s['daily_sharpe']) < 1e-12
assert abs(p['max_drawdown']-s['max_drawdown']) < 1e-12
assert abs(p['win_rate']-s['win_ratio']) < 1e-12
assert p['closed_trades'] == len(c)
assert p['valid_closed_trades'] == len(v)
assert abs(p['avg_return']-v.mean()) < 1e-12
assert abs(p['max_gain']-v.max()) < 1e-12
assert abs(p['max_loss']-v.min()) < 1e-12
assert len(d['holdings']) <= 10
assert all(r['entry_date'] is not None and r['exit_date'] is None for r in d['holdings'])
state = json.loads((ROOT/'watch2_pipeline/selections.json').read_text(encoding='utf-8'))
assert len({day[:7] for day in state['selections']}) == len(state['selections'])
assert all(len(x['picks']) <= 10 for x in state['selections'].values())
html = (ROOT/'_site/watch2/index.html').read_text(encoding='utf-8')
embedded = re.search(r'<script id="strategy-data" type="application/json">(.*?)</script>',html,re.S).group(1)
assert json.loads(embedded) == d
assert '__PAYLOAD_JSON__' not in html
for name in ['report.html','data.json','native_stats.json','trades.csv','nav.csv','validation.json']:
    assert (ROOT/'_site/watch2'/name).read_bytes() == (source/name).read_bytes()
for path in (ROOT/'2026').rglob('*'):
    if path.is_file():
        assert path.read_bytes() == (ROOT/'_site/2026'/path.relative_to(ROOT/'2026')).read_bytes()
print('PASS: eight cards, embedded data, native artifacts, immutable monthly structure, other dashboard unchanged.')
