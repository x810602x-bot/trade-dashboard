const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const StrategyAllocation=require('./allocation.js');
const source=fs.readFileSync(path.join(__dirname,'dashboard.js'),'utf8');
const template=fs.readFileSync(path.join(__dirname,'template.html'),'utf8');
const fixture=()=>JSON.parse(fs.readFileSync(path.join(__dirname,'../watch2/index.html'),'utf8').match(/<script id="strategy-data" type="application\/json">(.*?)<\/script>/s)[1]);

function render(data,now=Date.parse('2026-11-10T12:00:00+08:00')){
 const elements=new Map([...template.matchAll(/id="([^"]+)"/g)].map(([,id])=>[id,{textContent:'',innerHTML:'',hidden:false,addEventListener(type,handler){this[type]=handler;}}]));
 elements.get('strategy-data').textContent=JSON.stringify(data);
 // Target-lot cells are whatever the rendered buy and holding tables contain.
 let shares;
 const lotCells=()=>shares??=['pending','holdings'].flatMap(id=>[...elements.get(id).innerHTML.matchAll(/class="buy-shares" data-stock-id="([^"]+)"/g)].map(([,stockId])=>({dataset:{stockId},textContent:'—'})));
 const document={getElementById(id){assert(elements.has(id),`Missing element: ${id}`);return elements.get(id);},querySelectorAll(selector){return selector==='.buy-shares'?lotCells():[];}};
 const context=vm.createContext({document,StrategyAllocation,Date:{now:()=>now,parse:Date.parse}});
 vm.runInContext(source,context);
 assert.equal(vm.runInContext('JSON.stringify(d)',context),JSON.stringify(data),'Rendering must not change strategy data');
 return {elements,get shares(){return lotCells();},input(value){const box=elements.get('capital');box.value=value;box.input();},wholeLots(on){const box=elements.get('whole-lots');box.checked=on;box.change();}};
}

test('本期待賣與上期成交分開，未成交不顯示回測的參考賣價',()=>{
 const data=fixture();
 data.latest_selection={picks:['keep','new'],execution_date:'2026-10-13'};
 data.holdings=[
  {stock_id:'keep',name:'續留',entry_date:'2026-09-11',close:105,position:.1,'trade_price@entry_date':100},
  {stock_id:'sell',name:'本期移除',entry_date:'2026-09-11',exit_sig_date:'2026-10-12',close:110,'trade_price@entry_date':100,'trade_price@exit_date':9999}
 ];
 data.pending=[{stock_id:'new',name:'新增',entry_sig_date:'2026-10-12',close:50}];
 data.recent_sells=[{stock_id:'past',name:'上期',entry_date:'2026-08-11',exit_date:'2026-09-11','trade_price@entry_date':80,'trade_price@exit_date':90}];
 const {elements}=render(data);
 assert.equal(elements.get('holding-title').textContent,'持倉（1 檔）');
 assert.match(elements.get('holdings').innerHTML,/data-id="keep"/);
 assert.doesNotMatch(elements.get('holdings').innerHTML,/data-id="sell"/);
 assert.match(elements.get('sells').innerHTML,/data-id="sell"/);
 assert.doesNotMatch(elements.get('sells').innerHTML,/9,999|data-id="past"/);
 assert.match(elements.get('sells').innerHTML,/2026-10-13/);
 assert.match(elements.get('pending').innerHTML,/2026-10-13/);
 assert.match(elements.get('past-sells').innerHTML,/data-id="past"/);
 assert.match(elements.get('past-sells').innerHTML,/<td>90<\/td>/);
 assert.equal(elements.get('native-report').hidden,false);
 assert.match(elements.get('strategy-detail').textContent,/0\.0475%/);
});

test('更新時間放在上方；交易日 8 點前沒更新就變紅並警告',()=>{
 const data=fixture();
 data.generated_at='2026-11-10T07:27:30+08:00';
 data.stale_after='2026-11-11T08:00:00+08:00';
 let view=render(data,Date.parse('2026-11-11T07:59:00+08:00'));
 assert.equal(view.elements.get('updated').textContent,'更新時間 2026-11-10 07:27（台灣）');
 assert.equal(view.elements.get('updated').className,'sub');
 assert.doesNotMatch(view.elements.get('version').textContent,/更新時間/);
 view=render(data,Date.parse('2026-11-11T08:00:00+08:00'));
 assert.equal(view.elements.get('updated').className,'sub stale');
 assert.match(view.elements.get('updated').textContent,/⚠ 未如期更新/);
 delete data.stale_after;
 view=render(data,Date.parse('2030-01-01T00:00:00+08:00'));
 assert.equal(view.elements.get('updated').className,'sub');
});

test('教學按鈕開關說明層，引用的圖片都存在',()=>{
 const {elements}=render(fixture()), help=elements.get('help');
 elements.get('help-open').click();
 assert.equal(help.hidden,false);
 elements.get('help-close').click();
 assert.equal(help.hidden,true);
 elements.get('help-open').click();
 help.click({target:{}});
 assert.equal(help.hidden,false,'點說明內容不會關閉');
 help.click({target:help});
 assert.equal(help.hidden,true,'點旁邊空白處會關閉');
 const images=[...template.matchAll(/src="\.\.\/assets\/tutorial\/([^"]+)"/g)].map(m=>m[1]);
 assert.equal(images.length,3);
 images.forEach(name=>assert(fs.existsSync(path.join(__dirname,'tutorial',name)),`Missing ${name}`));
});

test('回測開始前的月份顯示「—」而不是 0%',()=>{
 const data=fixture();
 data.start='2008-03-10';
 data.monthly_returns={...data.monthly_returns,'2008-01':0,'2008-02':0,'2008-03':.027};
 const months=render(data).elements.get('months').innerHTML;
 assert.match(months,/<tr><td>2008<\/td><td><span class="dim">—<\/span><\/td><td><span class="dim">—<\/span><\/td><td><span class="pos">\+2\.7%<\/span><\/td>/);
});

test('原版沒有 exit_sig_date 時，仍按已保存名單顯示待賣股票',()=>{
 const data=fixture();
 data.latest_selection={picks:['keep']};
 data.holdings=[{stock_id:'keep'},{stock_id:'sell'}];
 data.pending=[];
 const {elements}=render(data);
 assert.equal(elements.get('holding-title').textContent,'持倉（1 檔）');
 assert.equal(elements.get('sells-title').textContent,'賣出（1 筆）');
 assert.match(elements.get('sells').innerHTML,/下個交易日/);
 assert.doesNotMatch(elements.get('sells').innerHTML,/undefined/);
});

test('空名單清倉、成交後轉持倉，不重複列為本期待賣',()=>{
 const data=fixture();
 data.latest_selection={picks:[],execution_date:'2026-10-13'};
 data.holdings=[{stock_id:'sell'}];
 data.pending=[];
 let view=render(data);
 assert.equal(view.elements.get('holding-title').textContent,'持倉（0 檔）');
 assert.equal(view.elements.get('sells-title').textContent,'賣出（1 筆）');
 data.latest_selection.picks=['new'];
 data.holdings=[{stock_id:'new',entry_date:'2026-10-13'}];
 data.recent_sells=[{stock_id:'sell',exit_date:'2026-10-13'}];
 view=render(data);
 assert.equal(view.elements.get('holding-title').textContent,'持倉（1 檔）');
 assert.equal(view.elements.get('sells-title').textContent,'賣出（0 筆）');
 assert.match(view.elements.get('past-sells').innerHTML,/data-id="sell"/);
});

test('買進張數沿用同一份配置計算，清空本金即清除舊張數',()=>{
 const data=fixture();
 data.latest_selection={picks:['keep','new'],execution_date:'2026-10-13'};
 data.holdings=[{stock_id:'keep',close:100,entry_date:'2026-09-11'}];
 data.pending=[{stock_id:'new',close:50}];
 data.allocation_prices={};
 const view=render(data);
 view.input('600');
 const expected=StrategyAllocation.allocate(6000000,[{stock_id:'keep',close:100},{stock_id:'new',close:50}],data.config.allocation);
 assert.equal(view.shares[0].textContent,StrategyAllocation.lotText(expected.rows[1].shares));
 assert.match(view.elements.get('holdings').innerHTML,/<th>目標張數<\/th>/);
 assert.equal(view.shares.find(c=>c.dataset.stockId==="keep").textContent,StrategyAllocation.lotText(expected.rows[0].shares),'續留股在持倉表顯示目標張數');
 assert.doesNotMatch(view.elements.get('sells').innerHTML,/目標張數/);
 assert.match(view.elements.get('allocation').innerHTML,/keep/);
 view.input('');
 assert.equal(view.shares[0].textContent,'—');
 assert.equal(view.elements.get('allocation-summary').textContent,'');
});

test('勾選只用整張：張數改成四捨五入的整張，並打開試算表看比例',()=>{
 const data=fixture();
 data.latest_selection={picks:['A','B'],execution_date:'2026-11-11'};
 data.holdings=[];
 data.pending=[{stock_id:'A',close:18.35},{stock_id:'B',close:66}];
 data.allocation_prices={A:{close:18.35},B:{close:66}};
 const view=render(data);
 view.input('50');
 assert.deepEqual(view.shares.map(c=>c.textContent),['2 張 720 股','756 股'].map((t,i)=>StrategyAllocation.lotText(StrategyAllocation.allocate(500000,[{close:18.35},{close:66}],data.config.allocation).rows[i].shares)));
 view.wholeLots(true);
 assert.deepEqual(view.shares.map(c=>c.textContent),['3 張','1 張']);
 assert.equal(view.elements.get('allocation-section').open,true);
 assert.match(view.elements.get('allocation').innerHTML,/<th>占總資產<\/th>/);
 assert.match(view.elements.get('allocation-summary').textContent,/占總資產/);
 view.wholeLots(false);
 assert.notEqual(view.shares[0].textContent,'3 張');
});
