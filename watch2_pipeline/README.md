# watch2 固定日期正式版

策略版本：`watch2-fixed10-v1`。本資料夾是 `/watch2/` 的唯一發布來源；不可改回舊網站的已實現獲利年平均算法。

## 已敲定規則

- 每月 10 日（含）起第一個台股交易日晚上選股，下一交易日開盤換股。
- 近 2 個月平均營收達近 12 個月最高；近 5 日至少 2 日達 200 日還原股價新高。
- 原始收盤價不超過 600 元，5 日平均成交金額大於 3,000 萬元，排除金融保險業及金融業。
- 營收年增率為正，依年增率選前 10 檔。每檔換股目標 10%，續留股票也按原生回測重新配置；不足 10 檔留現金。獲利再投入，無額外停損。
- FinLab 2.2.10 原生 `sim`：開盤成交，買賣手續費各 0.0475%，賣出證交稅 0.3%。未額外加入滑價或整張限制。

## 數據唯一來源

每次只建立一份 FinLab report。CAGR、每日夏普（年無風險利率 2%）、最大回撤、已平倉勝率與年月報酬均取 `get_stats()`；交易卡片與持股取 `get_trades()`，淨值取 `daily_creturn`。平均與單筆極值排除原生報酬缺值，頁面揭露缺值筆數。完整報表由原生 `to_html()` 產生。

2026-09-10 研究基準已重現：CAGR 34.01941656346643%、每日夏普 1.26335788772093、最大回撤 -30.5252992763152%。更新行情後數字自然變動，不能把 34.02% 寫死。

## 名單鎖定

`selections.json` 的 2008-03 至 2026-09 名單來自已核對研究回測，不宣稱當時已逐月保存，亦不能據此證明歷史資料沒有修訂。2026-10-12 起保存當晚實際產生的名單；任何既有紀錄都不可重算覆寫。

新名單只在訊號日台灣時間 22:00 起、下一交易日 09:00 前產生。不等金融保險業或全市場完成率。若當日行情或當期營收表尚未取得，更新失敗並保留前次網站；若已錯過開盤仍無保存名單，禁止用後來資料補造交易，需人工檢查。

## 發布與檢查

GitHub Pages 使用 Actions，主分支推送、手動執行及平日台灣時間 22:20 排程觸發。GitHub 排程可能延遲。兩頁都由 `dashboard_shared` 的同一份模板、績效統計與本金試算程式建立，不讀取舊發布器產生的 HTML。`/2026/` 保留自己的原交易引擎、費率及初始本金配置規則；詳見 `dashboard_shared/README.md`。

FinLab headless 登入使用官方支援的三個環境變數，存於 GitHub Actions encrypted secrets：`FINLAB_REFRESH_TOKEN`、`FINLAB_SESSION_ID`、`FINLAB_API_KEY`。不得將值、原始資料快取或憑證寫入 Git。

本機安裝 `requirements.txt` 後依序執行：

```sh
python -m unittest discover -s watch2_pipeline -p 'test_*.py'
python watch2_pipeline/update.py
python strategy2026_pipeline/update.py --cached
python watch2_pipeline/build.py
python watch2_pipeline/verify.py
```

`watch2_native/` 保存同份 report 的公開輸出，`_site/` 是發布成品；`.runtime/` 為忽略提交的工作快取。`update.py --reference` 需本機保留的原研究快取，會核对三個基準指標。

原本「觀察中策略」資料夾不在此流程的寫入範圍。不得回寫、修改或搬動其內容。
