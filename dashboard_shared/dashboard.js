
"use strict";
const d=JSON.parse(document.getElementById('strategy-data').textContent), p=d.performance, config=d.config;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=(v,n=2)=>v==null?'—':`${v>0?'+':''}${(v*100).toFixed(n)}%`;
const ret=(v,n=2)=>`<span class="${v>0?'pos':v<0?'neg':'dim'}">${pct(v,n)}</span>`;
const num=v=>v==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:2});
const date=v=>v?String(v).slice(0,10):'—';
document.getElementById('title').textContent=config.title;
document.getElementById('rules').innerHTML=config.rules.map(esc).join('<br>');
document.getElementById('date').textContent=`資料截至 ${d.date}｜回測自 ${d.start}｜本期選股日 ${d.selection_date}`;
const cards=[['複利年化 CAGR',pct(p.cagr),p.cagr],['夏普（每日）',p.sharpe.toFixed(2),null],['最大回撤',pct(p.max_drawdown),p.max_drawdown],['已平倉勝率',`${(p.win_rate*100).toFixed(1)}%`,null],['已平倉交易',`${num(p.closed_trades)} 筆`,null],['平均每筆報酬',pct(p.avg_return),p.avg_return],['單筆最大獲利',pct(p.max_gain),p.max_gain],['單筆最大虧損',pct(p.max_loss),p.max_loss]];
document.getElementById('metrics').innerHTML=cards.map(([label,value,color])=>`<div class="metric"><div class="metric-label">${label}</div><div class="metric-value ${color>0?'pos':color<0?'neg':''}">${value}</div></div>`).join('');
document.getElementById('method').textContent=`${config.engine_label}。CAGR、夏普及回撤依完整帳戶淨值計算，包含未賣出部位。${p.missing_return_trades?`${p.missing_return_trades} 筆已平倉交易缺少報酬值，未納入平均與單筆極值。`:''}`;
const years=Object.entries(d.yearly_returns).filter(([y])=>Number(y)>=Number(d.date.slice(0,4))-10);
document.getElementById('years').innerHTML=years.map(([y,v])=>`<div class="year" style="background:${v>=0?'rgba(219,39,119,.42)':'rgba(74,222,128,.22)'}"><strong>${pct(v,1)}</strong><span>${y}${y===d.date.slice(0,4)?' 至今':''}</span></div>`).join('');
const monthYears=[...new Set(Object.keys(d.monthly_returns).map(k=>k.slice(0,4)))];
document.getElementById('months').innerHTML=`<table class="monthly"><thead><tr><th>年份</th>${Array.from({length:12},(_,i)=>`<th>${i+1}月</th>`).join('')}</tr></thead><tbody>${monthYears.map(y=>`<tr><td>${y}</td>${Array.from({length:12},(_,i)=>`<td>${ret(d.monthly_returns[`${y}-${String(i+1).padStart(2,'0')}`],1)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
const weightLabel=config.allocation.mode==='keep'?'初始股款比例':'換股目標';
const selectedIds=new Set(d.latest_selection.picks);
const sellRows=d.holdings.filter(r=>r.exit_sig_date||!selectedIds.has(r.stock_id));
const holdingRows=d.holdings.filter(r=>!sellRows.includes(r));
const plannedDate=d.latest_selection.execution_date?date(d.latest_selection.execution_date):'下個交易日';
function stockTable(rows,mode){
 if(!rows.length)return `<div class="empty">${mode==='hold'?'本期沒有續留股票；預計賣出的股票列在「賣出」。':'目前沒有項目'}</div>`;
 if(mode==='buy')return `<table><thead><tr><th><button class="sort" type="button">名稱 ↕</button></th><th>狀態</th><th>最新收盤價</th><th>張數</th><th>${weightLabel}</th><th>買入日</th></tr></thead><tbody>${rows.map(r=>`<tr data-id="${esc(r.stock_id)}"><td>${esc(r.stock_id)} ${esc(r.name)}</td><td><span class="tag act-buy">新增</span></td><td>${num(r.close)}</td><td class="buy-shares" data-stock-id="${esc(r.stock_id)}">—</td><td>${pct(config.allocation.weight,0).replace('+','')}</td><td>${r.entry_date?date(r.entry_date):plannedDate}</td></tr>`).join('')}</tbody></table>`;
 const status=mode==='hold'?'持有':mode==='sell'?'移除':'已賣出';
 return `<table><thead><tr><th><button class="sort" type="button">名稱 ↕</button></th><th>狀態</th><th>漲跌</th><th>買入價</th><th>最新收盤價</th><th>賣出價</th><th>${weightLabel}</th><th>買入日</th><th>賣出日</th></tr></thead><tbody>${rows.map(r=>`<tr data-id="${esc(r.stock_id)}"><td>${esc(r.stock_id)} ${esc(r.name)}</td><td><span class="tag ${mode==='hold'?'act-hold':'act-sell'}">${status}</span></td><td>${ret(r.return)}</td><td>${num(r['trade_price@entry_date'])}</td><td>${num(r.close)}</td><td>${r.exit_date?num(r['trade_price@exit_date']):'—'}</td><td>${mode==='hold'?pct(r.position,0).replace('+',''):'—'}</td><td>${date(r.entry_date)}</td><td>${r.exit_date?date(r.exit_date):mode==='sell'?plannedDate:'—'}</td></tr>`).join('')}</tbody></table>`;
}
document.getElementById('holding-title').textContent=`持倉（${holdingRows.length} 檔）`;
document.getElementById('holdings').innerHTML=stockTable(holdingRows,'hold');
document.getElementById('pending-title').textContent=`買進（${d.pending.length} 筆）`;
document.getElementById('pending').innerHTML=stockTable(d.pending,'buy');
document.getElementById('sells-title').textContent=`賣出（${sellRows.length} 筆）`;
document.getElementById('sells').innerHTML=stockTable(sellRows,'sell');
document.getElementById('past-sells-title').textContent=`上期賣出（${d.recent_sells.length} 筆）`;
document.getElementById('past-sells').innerHTML=stockTable(d.recent_sells,'past');
document.getElementById('limits').textContent=d.limitations.join(' ');
document.getElementById('version').textContent=`${d.strategy_version}｜更新時間 ${d.generated_at.slice(0,19).replace('T',' ')}（台灣）`;
document.getElementById('native-report').hidden=!config.has_native_report;
document.getElementById('native-separator').hidden=!config.has_native_report;
const allocationConfig=config.allocation;
document.getElementById('capital-label').textContent=allocationConfig.capital_label;
document.getElementById('allocation-note').textContent=allocationConfig.mode==='keep'
 ?'輸入原始投入本金，以每檔初始本金 10% 的股款估算新建倉張數。已持有的續留股維持原張數，不照此表增減；獲利不會自動加大新倉。參考收盤價不等於實際成交價。'
 :'輸入換股時帳戶總資產，每檔以 10% 含買入手續費估算整張目標。續留股也調回目標；實際買賣張數需自行扣除現有持股。參考收盤價不等於實際成交價。';
document.getElementById('strategy-detail').textContent=`${config.detail} 夏普使用每日報酬及年無風險利率 2%。年度與月度報酬來自同一條淨值。交易筆數、勝率及單筆極值只計已平倉交易。買賣手續費各 ${pct(allocationConfig.fee_buy,4).replace('+','')}，賣出證交稅 ${pct(allocationConfig.tax_sell,1).replace('+','')}。`;
document.querySelectorAll('button.sort').forEach(b=>b.onclick=()=>{const body=b.closest('table').tBodies[0];const direction=b.dataset.desc==='1'?-1:1;b.dataset.desc=direction===1?'1':'0';[...body.rows].sort((a,c)=>direction*a.dataset.id.localeCompare(c.dataset.id,'zh-TW',{numeric:true})).forEach(r=>body.append(r));});
document.getElementById('capital').addEventListener('input',e=>{
 const capital=Number(e.target.value)*10000, box=document.getElementById('allocation'), summary=document.getElementById('allocation-summary');
 document.querySelectorAll('.buy-shares').forEach(cell=>cell.textContent='—');
 if(!Number.isFinite(capital)||capital<=0){box.textContent='';summary.textContent='';return;}
 const byId=new Map([...d.holdings,...d.pending].map(r=>[r.stock_id,r]));
 const stocks=d.latest_selection.picks.map(id=>{const held=byId.get(id),quote=d.allocation_prices?.[id];return {stock_id:id,name:held?.name||quote?.name||'',close:quote?.close??held?.close};});
 const result=StrategyAllocation.allocate(capital,stocks,allocationConfig);
 const lotsById=new Map(result.rows.map(r=>[r.stock_id,r.lots]));
 document.querySelectorAll('.buy-shares').forEach(cell=>{const lots=lotsById.get(cell.dataset.stockId);cell.textContent=lots==null?'缺參考價':`${lots} 張`;});
 const rows=result.rows.map(r=>`<tr><td>${esc(r.stock_id)} ${esc(r.name)}</td><td>${num(r.budget)}</td><td>${num(r.close)}</td><td>${r.lots===null?'缺參考價':`${r.lots} 張`}</td></tr>`);
 box.innerHTML=`<table><thead><tr><th>股票</th><th>${allocationConfig.budget_includes_fee?'每檔預算（含費）':'每檔股款上限'}</th><th>參考價</th><th>${allocationConfig.mode==='keep'?'新建倉參考':'整張目標'}</th></tr></thead><tbody>${rows.join('')}</tbody></table>`;
 summary.textContent=`${allocationConfig.mode==='keep'?'若這次全部新建倉：':''}估計使用 ${num(result.used)} 元（含買入手續費），剩餘現金 ${num(result.remaining)} 元。買不起一張或不足十檔的資金保留，不集中到其他股票。${result.missingPrice?' 有股票缺參考價，合計尚未包含該股。':''}`;
});
