const test=require('node:test');
const assert=require('node:assert/strict');
const {allocate,lotText}=require('./allocation.js');
const rebalance={weight:.1,fee_buy:.000475,budget_includes_fee:true};
const keep={weight:.1,fee_buy:.001425,budget_includes_fee:false};

test('600 萬、三檔：每檔仍以 60 萬為限，不把空倉資金集中',()=>{
  const result=allocate(6000000,[{stock_id:'A',close:100},{stock_id:'B',close:50},{stock_id:'C',close:200}],rebalance);
  assert.deepEqual(result.rows.map(x=>x.shares),[5997,11994,2998]);
  assert(result.remaining>4000000);
});
test('200 元版按換股總資產加大目標，手續費仍用原費率',()=>{
  const settings={...rebalance,fee_buy:.001425};
  const stocks=[{stock_id:'A',close:100}];
  const before=allocate(6000000,stocks,settings);
  const after=allocate(9000000,stocks,settings);
  assert.equal(before.rows[0].budget,600000);
  assert.equal(after.rows[0].budget,900000);
  assert.equal(before.rows[0].shares,5991);
  assert.equal(after.rows[0].shares,8987);
  assert(Math.abs(after.used-8987*100*(1+.001425))<1e-6);
});
test('原版固定初始股款保留，交易費另外扣；十檔不能超花本金',()=>{
  const result=allocate(6000000,Array.from({length:10},(_,i)=>({stock_id:String(i),close:100})),keep);
  assert.equal(result.rows[0].shares,6000);
  assert.equal(result.rows[9].shares,5914);
  assert(result.used<=6000000 && result.remaining>=0);
});
test('50 萬、200 元版四檔：一張買不起也用零股補到約 10%，合計約 40%',()=>{
  const settings={...rebalance,fee_buy:.001425};
  const result=allocate(500000,[{stock_id:'1416',close:18.35},{stock_id:'2412',close:159.5},{stock_id:'2468',close:66},{stock_id:'6112',close:57}],settings);
  assert.deepEqual(result.rows.map(x=>x.shares),[2720,313,756,875]);
  result.rows.forEach(r=>assert(r.cost<=50000 && r.cost>50000-r.close*1.01,`${r.stock_id} 應接近每檔 5 萬`));
  assert(result.used>199000 && result.used<=200000);
});
test('不把多餘資金塞入便宜股，名單順序不變',()=>{
  const result=allocate(100000,[{stock_id:'expensive',close:200},{stock_id:'cheap',close:5}],rebalance);
  assert.deepEqual(result.rows.map(x=>x.shares),[49,1999]);
  assert.equal(result.rows[0].stock_id,'expensive');
  assert(result.remaining>80000);
});
test('張數寫法：整張加零股',()=>{
  assert.equal(lotText(2720),'2 張 720 股');
  assert.equal(lotText(6000),'6 張');
  assert.equal(lotText(756),'756 股');
  assert.equal(lotText(0),'0 股');
  assert.equal(lotText(null),'缺參考價');
  assert.equal(lotText(undefined),'缺參考價');
});
test('缺價格不可當免費股票；無名單全留現金；無效本金不計算',()=>{
  assert.equal(allocate(100000,[{stock_id:'A',close:null}],rebalance).rows[0].shares,null);
  assert.equal(allocate(100000,[],rebalance).remaining,100000);
  assert.equal(allocate(Infinity,[],rebalance).rows.length,0);
});
