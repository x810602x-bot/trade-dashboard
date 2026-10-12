const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const StrategyAllocation=require('./allocation.js');
const source=fs.readFileSync(path.join(__dirname,'dashboard.js'),'utf8');
const template=fs.readFileSync(path.join(__dirname,'template.html'),'utf8');
const fixture=()=>JSON.parse(fs.readFileSync(path.join(__dirname,'../watch2/index.html'),'utf8').match(/<script id="strategy-data" type="application\/json">(.*?)<\/script>/s)[1]);

function render(data){
 const elements=new Map([...template.matchAll(/id="([^"]+)"/g)].map(([,id])=>[id,{textContent:'',innerHTML:'',hidden:false,addEventListener(type,handler){this[type]=handler;}}]));
 elements.get('strategy-data').textContent=JSON.stringify(data);
 const shares=data.pending.map(r=>({dataset:{stockId:r.stock_id},textContent:'—'}));
 const document={getElementById(id){assert(elements.has(id),`Missing element: ${id}`);return elements.get(id);},querySelectorAll(selector){return selector==='.buy-shares'?shares:[];}};
 const context=vm.createContext({document,StrategyAllocation});
 vm.runInContext(source,context);
 assert.equal(vm.runInContext('JSON.stringify(d)',context),JSON.stringify(data),'Rendering must not change strategy data');
 return {elements,shares,input(value){elements.get('capital').input({target:{value}});}};
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
 assert.equal(view.shares[0].textContent,`${expected.rows[1].lots} 張`);
 assert.match(view.elements.get('allocation').innerHTML,/keep/);
 view.input('');
 assert.equal(view.shares[0].textContent,'—');
 assert.equal(view.elements.get('allocation-summary').textContent,'');
});
