"""Publish watch2 only from the native source; ignore legacy generated HTML."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]


def build():
    source = ROOT/'watch2_native'
    payload = json.loads((source/'data.json').read_text(encoding='utf-8'))
    assert payload['strategy_version'] == 'watch2-fixed10-v1'
    stats = json.loads((source/'native_stats.json').read_text(encoding='utf-8'))
    for key,native in [('cagr','cagr'),('sharpe','daily_sharpe'),('max_drawdown','max_drawdown'),('win_rate','win_ratio')]:
        assert payload['performance'][key] == stats[native]
    html = (ROOT/'watch2_pipeline/template.html').read_text(encoding='utf-8').replace(
        '__PAYLOAD_JSON__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/'))
    site = ROOT/'_site'
    site.mkdir(exist_ok=True)
    # Preserve the other existing dashboard and any of its assets.
    shutil.copytree(ROOT/'2026',site/'2026',dirs_exist_ok=True)
    output = site/'watch2'
    output.mkdir(exist_ok=True)
    (output/'index.html').write_text(html,encoding='utf-8')
    (ROOT/'watch2/index.html').write_text(html,encoding='utf-8')
    for name in ['data.json','native_stats.json','report.html','trades.csv','nav.csv','validation.json']:
        shutil.copy2(source/name,output/name)
    (site/'.nojekyll').touch()
    print(f'Built fixed-date watch2 for {payload["date"]}; legacy watch2 HTML is never used as input.')


if __name__ == '__main__':
    build()
