"""Build both dashboards from one template and shared assets, never legacy HTML."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard_shared.strategies import CONFIGS


def build():
    shared=ROOT/'dashboard_shared';site=ROOT/'_site'
    (site/'assets').mkdir(parents=True,exist_ok=True)
    names=['dashboard.css','dashboard.js','allocation.js']
    version=hashlib.sha256(b''.join((shared/n).read_bytes() for n in names)).hexdigest()[:12]
    for name in names:
        shutil.copy2(shared/name,site/'assets'/name)
    for page,config in CONFIGS.items():
        source=ROOT/('watch2_native' if page=='watch2' else 'strategy2026_native')
        payload=json.loads((source/'data.json').read_text(encoding='utf-8'))
        assert payload['strategy_version']==config['strategy_version']
        stats=json.loads((source/'native_stats.json').read_text(encoding='utf-8'))
        assert all(payload['performance'][key]==stats[native] for key,native in
            [('cagr','cagr'),('sharpe','daily_sharpe'),('max_drawdown','max_drawdown')])
        payload['config']=config
        text=(shared/'template.html').read_text(encoding='utf-8').replace('__TITLE__',html.escape(config['title'])).replace('__ASSET_VERSION__',version)
        text=text.replace('__PAYLOAD_JSON__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/'))
        output=site/page;output.mkdir(exist_ok=True)
        (output/'index.html').write_text(text,encoding='utf-8')
        (ROOT/page/'index.html').write_text(text,encoding='utf-8')
        for name in ['data.json','native_stats.json','trades.csv','nav.csv','validation.json']+(['report.html'] if config['has_native_report'] else []):
            shutil.copy2(source/name,output/name)
        print(f'Built {page}: {payload["date"]}, {payload["performance"]["cagr"]:.4%}')
    (site/'.nojekyll').touch()

if __name__=='__main__':
    build()
