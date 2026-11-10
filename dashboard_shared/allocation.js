/* Shared share-count estimate: whole lots plus odd lots, so each stock reaches its target like the backtest. */
(function(root){
  'use strict';
  function allocate(capital,stocks,settings){
    if(!Number.isFinite(capital)||capital<=0) return {rows:[],used:0,remaining:0,missingPrice:false};
    let remaining=capital;
    const rows=stocks.map(stock=>{
      const price=Number(stock.close),budget=capital*settings.weight;
      if(!Number.isFinite(price)||price<=0) return {...stock,budget,shares:null,cost:null};
      const shareCost=price*(1+settings.fee_buy);
      const shares=Math.max(0,Math.min(Math.floor(budget/(settings.budget_includes_fee?shareCost:price)),Math.floor((remaining+1e-8)/shareCost)));
      const cost=shares*shareCost;
      remaining-=cost;
      return {...stock,budget,shares,cost};
    });
    return {rows,used:capital-remaining,remaining,missingPrice:rows.some(r=>r.shares===null)};
  }
  /* 2720 -> "2 張 720 股"; 6000 -> "6 張"; 756 -> "756 股". */
  function lotText(shares){
    if(shares==null) return '缺參考價';
    const lots=Math.floor(shares/1000),odd=shares%1000;
    return lots&&odd?`${lots} 張 ${odd} 股`:lots?`${lots} 張`:`${odd} 股`;
  }
  if(typeof module!=='undefined')module.exports={allocate,lotText};
  else root.StrategyAllocation={allocate,lotText};
})(typeof globalThis!=='undefined'?globalThis:this);
