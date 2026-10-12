const test=require('node:test');
const assert=require('node:assert/strict');
const {allocate}=require('./allocation.js');
const rebalance={weight:.1,fee_buy:.000475,budget_includes_fee:true};
const keep={weight:.1,fee_buy:.001425,budget_includes_fee:false};

test('600 萬、三檔：每檔仍以 60 萬為限，不把空倉資金集中',()=>{
  const result=allocate(6000000,[{stock_id:'A',close:100},{stock_id:'B',close:50},{stock_id:'C',close:200}],rebalance);
  assert.deepEqual(result.rows.map(x=>x.lots),[5,11,2]);
  assert(result.remaining>4000000);
});
test('200 元版按換股總資產加大目標，手續費仍用原費率',()=>{
  const settings={...rebalance,fee_buy:.001425};
  const stocks=[{stock_id:'A',close:100}];
  const before=allocate(6000000,stocks,settings);
  const after=allocate(9000000,stocks,settings);
  assert.equal(before.rows[0].budget,600000);
  assert.equal(after.rows[0].budget,900000);
  assert.equal(before.rows[0].lots,5);
  assert.equal(after.rows[0].lots,8);
  assert.equal(after.used,800000*(1+.001425));
});
test('原版固定初始股款保留，交易費另外扣；十檔不能超花本金',()=>{
  const result=allocate(6000000,Array.from({length:10},(_,i)=>({stock_id:String(i),close:100})),keep);
  assert.equal(result.rows[0].lots,6);
  assert.equal(result.rows[9].lots,5);
  assert(result.used<=6000000 && result.remaining>=0);
});
test('買不起整張時不改股票名單、不把多餘資金塞入便宜股',()=>{
  const result=allocate(100000,[{stock_id:'expensive',close:200},{stock_id:'cheap',close:5}],rebalance);
  assert.deepEqual(result.rows.map(x=>x.lots),[0,1]);
  assert.equal(result.rows[0].stock_id,'expensive');
});
test('缺價格不可當免費股票；無名單全留現金；無效本金不計算',()=>{
  assert.equal(allocate(100000,[{stock_id:'A',close:null}],rebalance).rows[0].lots,null);
  assert.equal(allocate(100000,[],rebalance).remaining,100000);
  assert.equal(allocate(Infinity,[],rebalance).rows.length,0);
});
