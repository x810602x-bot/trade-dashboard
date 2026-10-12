import numpy as np

# ── 讀取開盤價（還原股價） ──
open_price = gat("etl#adj_open")

# ── 建立換股交易日清單 ──
# rebalance_map: signal_date → rebalance_date（前一個 cell 已建好）
# 反向對照：rebalance_date → signal_date
rebalance_to_signal = {v: k for k, v in rebalance_map.items() if k in holdings}
rebalance_dates_list = sorted(rebalance_to_signal.keys())

# ── 逐日回測 ──
nav = 1.0
cash = 1.0
positions = {}             # {stock_id: {"buy_price": float, "shares": float, "buy_date": date}}
nav_series = {}
trade_log = []
daily_history = {}

realized_nav = 1.0
realized_nav_series = {}

rebal_idx = 0

bt_start = rebalance_dates_list[0] if rebalance_dates_list else trading_days[0]

for date in trading_days:
    if date < bt_start:
        continue

    today_close = close.loc[date]
    today_open = open_price.loc[date] if date in open_price.index else today_close
    bought_today = []
    sold_today = []

    # ── 1. 換股日處理（在 rebalance_date 執行，用訊號日的選股結果） ──
    is_rebalance = False
    new_picks = []
    signal_date = None
    if rebal_idx < len(rebalance_dates_list) and date >= rebalance_dates_list[rebal_idx]:
        is_rebalance = True
        rebal_date = rebalance_dates_list[rebal_idx]
        signal_date = rebalance_to_signal[rebal_date]
        new_picks = list(holdings[signal_date].index)
        rebal_idx += 1

    # ── 2. 換股賣出（賣掉不在新名單的） ──
    if is_rebalance:
        for sid in list(positions.keys()):
            if sid in new_picks:
                continue
            sell_price = today_open[sid] if sid in today_open.index and not pd.isna(today_open[sid]) else today_close.get(sid, None)
            if sell_price is None or pd.isna(sell_price):
                continue
            pos = positions.pop(sid)
            proceeds = pos["shares"] * sell_price * (1 - FEE_SELL) * (1 - TAX_SELL)
            cash += proceeds
            ret = (sell_price / pos["buy_price"]) * (1 - FEE_SELL) * (1 - TAX_SELL) / (1 + FEE_BUY) - 1
            trade_log.append({
                "stock_id": sid, "buy_date": pos["buy_date"], "sell_date": date,
                "buy_price": pos["buy_price"], "sell_price": sell_price,
                "return": ret, "reason": "換股",
            })
            sold_today.append(sid)
            realized_nav += ret * (1.0 / MAX_POSITIONS)

    # ── 3. 換股日買入新標的（用今日開盤價，每檔固定買初始資金的 10%） ──
    if is_rebalance and new_picks:
        to_buy = [s for s in new_picks if s not in positions]
        if to_buy:
            per_stock = 1.0 / MAX_POSITIONS  # 固定金額：初始資金的 10%
            for sid in to_buy:
                buy_price = today_open[sid] if sid in today_open.index and not pd.isna(today_open[sid]) else None
                if buy_price is None or pd.isna(buy_price) or buy_price <= 0:
                    continue
                cost = per_stock * (1 + FEE_BUY)
                if cost > cash:
                    cost = cash
                if cost <= 0:
                    continue
                shares = cost / buy_price / (1 + FEE_BUY)
                cash -= shares * buy_price * (1 + FEE_BUY)
                positions[sid] = {"buy_price": buy_price, "shares": shares, "buy_date": date}
                bought_today.append(sid)

    # ── 4. 計算今日淨值 ──
    pos_value = sum(
        pos["shares"] * (today_close[sid] if sid in today_close.index and not pd.isna(today_close[sid]) else pos["buy_price"])
        for sid, pos in positions.items()
    )
    nav = cash + pos_value
    nav_series[date] = nav
    realized_nav_series[date] = realized_nav

    # ── 5. 記錄每日持股 ──
    daily_history[date.strftime("%Y-%m-%d")] = {
        "holdings": sorted(positions.keys()),
        "buy": bought_today,
        "sell": sold_today,
        "holding_count": len(positions),
    }

