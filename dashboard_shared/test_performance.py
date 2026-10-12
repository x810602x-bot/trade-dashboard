import json
from pathlib import Path
import unittest
import pandas as pd
from dashboard_shared.performance import measure

ROOT=Path(__file__).resolve().parents[1]

class MeasurementTests(unittest.TestCase):
    def test_unrealized_loss_counts_in_drawdown(self):
        nav=pd.Series([100.,120.,60.]+[100.]*257,index=pd.bdate_range('2020-01-01',periods=260))
        trades=pd.DataFrame({'entry_date':[pd.Timestamp('2020-01-01')],'exit_date':[pd.NaT],'return':[0.]})
        p,*_=measure(nav,trades)
        self.assertEqual(p['closed_trades'],0)
        self.assertEqual(p['cagr'],0)
        self.assertAlmostEqual(p['max_drawdown'],-.5)

    def test_watch2_all_saved_stats_stay_identical(self):
        folder=ROOT/'watch2_native'
        nav=pd.read_csv(folder/'nav.csv',index_col=0,parse_dates=True).iloc[:,0]
        trades=pd.read_csv(folder/'trades.csv')
        stats=json.loads((folder/'native_stats.json').read_text(encoding='utf-8'))
        old=json.loads((folder/'data.json').read_text(encoding='utf-8'))
        p,y,m,_=measure(nav,trades,stats)
        for key,value in old['performance'].items():
            if value is not None:self.assertAlmostEqual(p[key],value,places=10)
        self.assertEqual(y,old['yearly_returns'])
        self.assertEqual(m,old['monthly_returns'])

if __name__=='__main__':unittest.main()
