"""Page-specific rules; calculation and UI are shared."""
CONFIGS={
 'watch2':{
  'strategy_version':'watch2-fixed10-v1','title':'每月換股策略（固定日期・10 檔）',
  'rules':['股價 ≤ 600 元｜5 日均成交金額 > 3,000 萬｜排除金融保險業',
    '每月 10 號（含）後首個交易日晚上選股，下一交易日開盤換股',
    '最多 10 檔，每檔換股目標 10%；續留股也重新配置，不足額留現金，獲利再投入'],
  'detail':'近 2 個月平均營收達近 12 個月最高；近 5 天至少 2 天達 200 日新高。通過篩選後，取營收年增率為正的前 10 檔。沒有另加停損。',
  'engine_label':'FinLab 原生回測','has_native_report':True,
  'allocation':{'mode':'rebalance','capital_label':'換股時帳戶總資產','weight':.1,'fee_buy':.000475,'fee_sell':.000475,'tax_sell':.003,'budget_includes_fee':True},
 },
 '2026':{
  'strategy_version':'2026-original-v1','title':'每月換股策略（200 元原版）',
  'rules':['股價 ≤ 200 元｜5 日均成交量 > 50 萬股｜排除金融保險業',
    '每月 10 號後等營收條件到齊；未齊最多順延 5 個交易日，名單鎖定後下一交易日開盤換股',
    '最多選 10 檔；新股買初始本金的 10%，續留股不動，獲利保留現金'],
  'detail':'近 2 個月平均營收達近 12 個月最高；近 5 天至少 2 天達 200 日新高。符合條件且營收年增率為正，依年增率取前 10 檔。保留原版等營收、鎖名單、缺價處理及無合格名單不換股的行為。沒有另加停損。',
  'engine_label':'原交易規則＋FinLab 淨值統計','has_native_report':False,
  'allocation':{'mode':'keep','capital_label':'原始投入本金','weight':.1,'fee_buy':.001425,'fee_sell':.001425,'tax_sell':.003,'budget_includes_fee':False},
 }
}
