import copy
from datetime import datetime
import unittest
from unittest import mock
import pandas as pd
from strategy2026_pipeline.update import append_selection,TZ


class PreservedDecisions(unittest.TestCase):
    def test_locked_month_is_not_reselected(self):
        state={'live_from':'2026-10-12','selections':{'2026-10-12':{'picks':['2606']}}}
        old=copy.deepcopy(state)
        close=pd.DataFrame({'2606':[77.]},index=pd.to_datetime(['2026-10-12']))
        get=mock.Mock(return_value=close)
        append_selection(state,get,None,datetime(2026,10,12,23,tzinfo=TZ),close.index[-1])
        self.assertEqual(state,old)
        self.assertEqual(get.call_count,2)

    def test_daytime_does_not_publish_even_with_closing_data(self):
        state={'live_from':'2026-10-12','selections':{}}
        close=pd.DataFrame({'2606':[77.]},index=pd.to_datetime(['2026-10-12']))
        with mock.patch('strategy2026_pipeline.update.data.get_calendar'):
            append_selection(state,lambda _:close,None,datetime(2026,10,12,20,tzinfo=TZ),close.index[-1])
        self.assertEqual(state['selections'],{})

    def test_stale_prices_do_not_backfill_an_order(self):
        state={'live_from':'2026-10-12','selections':{}}
        close=pd.DataFrame({'2606':[77.]},index=pd.to_datetime(['2026-10-12']))
        cal=mock.Mock();cal.open_at.return_value=datetime(2026,10,13,9,tzinfo=TZ)
        with mock.patch('strategy2026_pipeline.update.data.get_calendar',return_value=cal):
            with self.assertRaisesRegex(RuntimeError,'stale'):
                append_selection(state,lambda _:close,None,datetime(2026,10,13,23,tzinfo=TZ),close.index[-1])

if __name__=='__main__':unittest.main()
