# 兩頁共用的績效與本金試算

`performance.py` 用 FinLab 的 `metrics_from_nav` 計算完整淨值的 CAGR、每日夏普及最大回撤；年、月報酬採 FinLab 隨附的 `PerformanceStats`。原生 report 的輸出會核對為相同數字。交易卡片只使用已平倉紀錄。

`template.html`、`dashboard.js`、`dashboard.css`、`allocation.js` 各只有一份。每個頁面差異集中於 `strategies.py`，本金不會改股票名單；不足一張／不足十檔的餘額不集中投入其他股票。缺價格明確顯示，不拿零元代替。

| 規則 | 2026 原版 | watch2 |
|---|---|---|
| 股價／流動性 | ≤200 元／5 日均量>50 萬股 | ≤600 元／5 日均成交金額>3,000 萬 |
| 訊號 | 保留營收到齊守門員及鎖定 | 固定日期及鎖定 |
| 新股買入 | 換股時帳戶淨值的10%目標 | 換股時帳戶淨值的10%目標 |
| 續留股 | 每次換股重配至10% | 每月重配至10% |
| 每邊手續費 | 0.1425% | 0.0475% |
| 賣出稅 | 0.3% | 0.3% |
| 交易引擎 | FinLab sim | FinLab sim |

2026/10/12 依使用者要求，200 元版改為 `2026-reinvest-v2`，全部歷史用與 watch2 相同的 FinLab sim 資金配置與缺價處理重算；每次換股依當時總資產重新配置，獲利再投入。每檔最多 10%，不足十檔的餘額留現金；不模擬指定本金或整張限制。兩版都直接發布 report.to_html 產生的原生報表。

原 200 元版引擎仍保存在 `strategy2026_pipeline/source/original_engine.py`，初次遷移曾核對1,437筆交易及完整逐日淨值相同；已不再用於網站更新。歷史選股名單保存於各自的 selections.json，名單檔原版本名稱表示選股來源，頁面版本另行標示資金配置的改版。2026年8月原版先重算、再鎖名單造成的兩次換股保留，不能把這段歷史當作當時已保存的真實訊號。

## 更新及驗證

GitHub Actions 先更新 watch2 與共用行情快取，再更新 2026。兩者選股檔各自保存、既有名單不可改寫；未到22:00不產生今晚新名單。2026 原版沒有合格名單時不換股，與 watch2 空名單清倉的規則不同。此差異保留在策略端，沒有混入共用統計或畫面。

執行 `python dashboard_shared/build.py`、`python dashboard_shared/verify.py` 會重建及核對兩頁。`watch2_pipeline/build.py` 與 `verify.py` 只保留相容入口，實際呼叫共用模組。發布成品在 `_site`，預覽須從該目錄啟動 HTTP server。歷史原始行情、登入憑證與測試工作檔只留在忽略提交的 `.runtime`。

檢查：`python -m unittest discover -s watch2_pipeline -p 'test_*.py'`；`python -m unittest discover -s dashboard_shared -p 'test_*.py'`；`node --test dashboard_shared/test_allocation.cjs`。

禁止寫入原「觀察中策略」目錄。原排程即使再推送舊 HTML，Pages 都會用上述來源重新建立兩頁，不會退回舊算法。
