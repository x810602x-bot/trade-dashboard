/* Shared whole-lot estimate. Strategy settings supply sizing and fee differences. */
(function(root){
  'use strict';
  function allocate(capital,stocks,settings){
    if(!Number.isFinite(capital)||capital<=0) return {rows:[],used:0,remaining:0,missingPrice:false};
    let remaining=capital;
    const rows=stocks.map(stock=>{
      const price=Number(stock.close),budget=capital*settings.weight;
      if(!Number.isFinite(price)||price<=0) return {...stock,budget,lots:null,cost:null};
      const shareCost=price*1000,lotCost=shareCost*(1+settings.fee_buy);
      const lots=Math.max(0,Math.min(Math.floor(budget/(settings.budget_includes_fee?lotCost:shareCost)),Math.floor((remaining+1e-8)/lotCost)));
      const cost=lots*lotCost;
      remaining-=cost;
      return {...stock,budget,lots,cost};
    });
    return {rows,used:capital-remaining,remaining,missingPrice:rows.some(r=>r.lots===null)};
  }
  if(typeof module!=='undefined')module.exports={allocate};
  else root.StrategyAllocation={allocate};
})(typeof globalThis!=='undefined'?globalThis:this);
