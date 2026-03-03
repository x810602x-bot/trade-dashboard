"""
讀取 ../watchlist.json，產出 index.html（深色主題靜態頁面）。
"""

import json
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(SCRIPT_DIR, '..', 'watchlist.json')
HTML_PATH = os.path.join(SCRIPT_DIR, 'index.html')

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
    background: #0d1117; color: #c9d1d9; padding: 24px;
    max-width: 800px; margin: 0 auto;
}
h1 { color: #58a6ff; font-size: 1.4em; margin-bottom: 4px; }
.subtitle { color: #8b949e; font-size: 0.85em; margin-bottom: 24px; }
.day { background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 12px; }
.day-header {
    padding: 12px 16px; cursor: pointer; display: flex;
    justify-content: space-between; align-items: center;
    user-select: none;
}
.day-header:hover { background: #1c2129; border-radius: 8px; }
.day-date { font-weight: bold; color: #f0f6fc; }
.day-meta { display: flex; gap: 12px; align-items: center; font-size: 0.85em; }
.regime-bull { color: #3fb950; }
.regime-bear { color: #f85149; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
.badge-buy { background: #0d4429; color: #3fb950; }
.badge-sell { background: #4a1c1c; color: #f85149; }
.badge-hold { background: #1c2333; color: #58a6ff; }
.day-body { padding: 0 16px 16px; display: none; }
.day.open .day-body { display: block; }
.day.open .arrow { transform: rotate(90deg); }
.arrow { color: #484f58; transition: transform 0.15s; display: inline-block; }
.section-label { color: #8b949e; font-size: 0.8em; margin: 12px 0 6px; text-transform: uppercase; }
.stock-list { display: flex; flex-wrap: wrap; gap: 6px; }
.stock {
    background: #21262d; padding: 4px 10px; border-radius: 4px;
    font-size: 0.9em; color: #c9d1d9;
}
.stock-buy { border-left: 3px solid #3fb950; }
.stock-sell { border-left: 3px solid #f85149; text-decoration: line-through; color: #8b949e; }
.empty { color: #484f58; font-style: italic; font-size: 0.85em; }
footer { text-align: center; color: #484f58; font-size: 0.75em; margin-top: 32px; }
"""

JS = """
document.querySelectorAll('.day-header').forEach(h => {
    h.addEventListener('click', () => h.parentElement.classList.toggle('open'));
});
"""


def generate():
    if not os.path.exists(JSON_PATH):
        print(f'[錯誤] 找不到 {JSON_PATH}')
        raise SystemExit(1)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        watchlist = json.load(f)

    if not watchlist:
        print('[錯誤] watchlist.json 是空的')
        raise SystemExit(1)

    sorted_dates = sorted(watchlist.keys(), reverse=True)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    days_html = []
    for i, date_str in enumerate(sorted_dates):
        entry = watchlist[date_str]
        holdings = entry.get('holdings', [])
        buy = entry.get('buy', [])
        sell = entry.get('sell', [])
        count = entry.get('holding_count', len(holdings))
        regime = entry.get('regime', 'bull')

        regime_cls = 'regime-bull' if regime == 'bull' else 'regime-bear'
        regime_text = '\u2191 \u591a\u982d' if regime == 'bull' else '\u2193 \u7a7a\u982d'
        open_cls = ' open' if i == 0 else ''

        meta_parts = [f'<span class="{regime_cls}">{regime_text}</span>']
        meta_parts.append(f'<span class="badge badge-hold">{count} \u6a94</span>')
        if buy:
            meta_parts.append(f'<span class="badge badge-buy">+{len(buy)}</span>')
        if sell:
            meta_parts.append(f'<span class="badge badge-sell">-{len(sell)}</span>')

        # Holdings section
        holdings_html = ''.join(f'<span class="stock">{s}</span>' for s in holdings)
        if not holdings:
            holdings_html = '<span class="empty">\u7121\u6301\u80a1</span>'

        # Buy section
        buy_html = ''
        if buy:
            buy_items = ''.join(f'<span class="stock stock-buy">{s}</span>' for s in buy)
            buy_html = f'<div class="section-label">\u8cb7\u9032</div><div class="stock-list">{buy_items}</div>'

        # Sell section
        sell_html = ''
        if sell:
            sell_items = ''.join(f'<span class="stock stock-sell">{s}</span>' for s in sell)
            sell_html = f'<div class="section-label">\u8ce3\u51fa</div><div class="stock-list">{sell_items}</div>'

        days_html.append(f"""
<div class="day{open_cls}">
  <div class="day-header">
    <div><span class="arrow">\u25b6</span> <span class="day-date">{date_str}</span></div>
    <div class="day-meta">{''.join(meta_parts)}</div>
  </div>
  <div class="day-body">
    <div class="section-label">\u6301\u80a1</div>
    <div class="stock-list">{holdings_html}</div>
    {buy_html}
    {sell_html}
  </div>
</div>""")

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>\u898f\u5247\u53e2\u96c6\u6295\u7968\u7b56\u7565</title>
<style>{CSS}</style>
</head>
<body>
<h1>\u898f\u5247\u53e2\u96c6\u6295\u7968\u7b56\u7565</h1>
<div class="subtitle">vote_v5_zscore_hedge \u00b7 8 \u898f\u5247 \u2265 5 \u7968 \u00b7 \u66f4\u65b0\u6642\u9593 {now}</div>
{''.join(days_html)}
<footer>\u7531 run_strategy.py \u81ea\u52d5\u7522\u751f \u00b7 \u8cc7\u6599\u4f86\u6e90 FinLab</footer>
<script>{JS}</script>
</body>
</html>"""

    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'[OK] 已產生 {HTML_PATH} ({len(sorted_dates)} 天)')


if __name__ == '__main__':
    generate()
