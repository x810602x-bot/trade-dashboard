import json
from pathlib import Path
import unittest
import pandas as pd
from datetime import date, datetime
from unittest import mock
from zoneinfo import ZoneInfo
from finlab.session_calendar import CalendarUnavailable
from dashboard_shared.performance import measure, fix_continuing_returns, merge_kept, stale_after

ROOT=Path(__file__).resolve().parents[1]

class MeasurementTests(unittest.TestCase):
    def test_stale_after_waits_for_the_next_nightly_run(self):
        tw=ZoneInfo('Asia/Taipei')
        calendar=mock.Mock()
        calendar.next_session.side_effect=lambda d:{date(2026,11,13):date(2026,11,16),date(2026,11,16):date(2026,11,17)}[d]
        friday=pd.Timestamp('2026-11-13')
        # Nightly run (even if GitHub starts it after midnight): next night's run is due Tuesday 08:00.
        self.assertEqual(stale_after(calendar,friday,datetime(2026,11,14,3,tzinfo=tw)),'2026-11-17T08:00:00+08:00')
        # Daytime run on the data date: that night's run is still due by Monday 08:00.
        self.assertEqual(stale_after(calendar,friday,datetime(2026,11,13,19,55,tzinfo=tw)),'2026-11-16T08:00:00+08:00')
        calendar.next_session.side_effect=CalendarUnavailable('outside coverage')
        self.assertEqual(stale_after(calendar,pd.Timestamp('2026-12-31'),datetime(2026,12,31,23,tzinfo=tw)),'2027-01-04T08:00:00+08:00')

    def test_unrealized_loss_counts_in_drawdown(self):
        nav=pd.Series([100.,120.,60.]+[100.]*257,index=pd.bdate_range('2020-01-01',periods=260))
        trades=pd.DataFrame({'entry_date':[pd.Timestamp('2020-01-01')],'exit_date':[pd.NaT],'return':[0.]})
        p,*_=measure(nav,trades)
        self.assertEqual(p['closed_trades'],0)
        self.assertEqual(p['cagr'],0)
        self.assertAlmostEqual(p['max_drawdown'],-.5)

    def test_kept_stock_split_is_repriced_open_to_open(self):
        days=pd.to_datetime(['2009-09-11','2009-10-13','2009-11-11'])
        adj_open=pd.DataFrame({'2499':[62.19,68.41,63.19],'2330':[10.,11.,12.]},index=days)
        trades=pd.DataFrame({'stock_id':['2499','2499','2330'],'entry_date':[days[0],days[1],days[0]],
            'exit_date':[days[1],days[2],days[2]],'return':[.1674,-.0796,.25]})
        fixed=fix_continuing_returns(trades,adj_open,.000475,.003)
        self.assertAlmostEqual(fixed.at[0,'return'],68.41/62.19*(1-.000475)*(1-.000475-.003)-1)
        self.assertEqual(fixed['return'][1:].tolist(),[-.0796,.25])
        self.assertEqual(fixed['return_native'].tolist(),[.1674,-.0796,.25])

    def test_kept_stock_parts_show_as_one_holding(self):
        d=pd.to_datetime(['2026-09-11','2026-10-13','2026-11-10','2026-11-11'])
        adj_open=pd.DataFrame({'A':[100.,110.,0,120.],'B':[50.,55.,0,60.],'C':[10.,11.,0,12.]},index=d)
        adj_close=pd.DataFrame({'A':[0,0,130.,0],'B':[0,0,0,0],'C':[0,0,0,0]},index=d)
        nat=pd.NaT
        trades=pd.DataFrame({'stock_id':['A','A','B','B','C','D'],
            'entry_date':[d[0],d[1],d[0],d[1],d[0],nat],'exit_date':[d[1],nat,d[1],d[3],d[1],nat],
            'entry_sig_date':[d[0],d[1],d[0],d[1],d[0],d[2]],'exit_sig_date':[d[1],nat,d[1],d[2],d[1],nat],
            'trade_price@entry_date':[100,110,50,55,10,None],'trade_price@exit_date':[110,None,55,60,11,None],
            'position':[.1,.1,.1,.1,.1,None],'return':[.09,.18,.09,.09,.09,None]})
        shown=merge_kept(trades,adj_open,adj_close,d[2],.000475,.003).set_index('stock_id')
        self.assertEqual(list(shown.index),['A','B','C','D'])
        # Kept A: one open holding from its first buy, priced like FinLab's open trades.
        self.assertEqual(shown.at['A','entry_date'],d[0]);self.assertTrue(pd.isna(shown.at['A','exit_date']))
        self.assertEqual(shown.at['A','trade_price@entry_date'],100)
        self.assertAlmostEqual(shown.at['A','return'],130/100*(1-.000475)-1)
        # Kept B then sold: one closed trade from first buy to final sell.
        self.assertEqual((shown.at['B','entry_date'],shown.at['B','exit_date']),(d[0],d[3]))
        self.assertAlmostEqual(shown.at['B','return'],60/50*(1-.000475)*(1-.000475-.003)-1)
        # Ordinary sale and pending buy are untouched.
        self.assertEqual(shown.at['C','return'],.09);self.assertTrue(pd.isna(shown.at['D','entry_date']))

    def test_trade_pending_for_next_open_is_left_alone(self):
        days=pd.to_datetime(['2026-10-13','2026-11-10'])
        adj_open=pd.DataFrame({'1303':[50.,52.],'6870':[400.,440.]},index=days)
        trades=pd.DataFrame({'stock_id':['1303','6870'],'entry_date':[days[0],pd.NaT],
            'exit_date':[pd.NaT,pd.NaT],'return':[.04,None]})
        fixed=fix_continuing_returns(trades,adj_open,.000475,.003)
        self.assertEqual(fixed.at[0,'return'],.04)
        self.assertTrue(pd.isna(fixed.at[1,'return']))

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
