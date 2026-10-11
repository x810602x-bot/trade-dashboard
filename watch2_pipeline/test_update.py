import copy
from datetime import datetime, date
from unittest import TestCase, mock
import pandas as pd
from update import append_selection, position_from_state, TZ


class Decisions(TestCase):
    def test_empty_month_is_cash_not_missing_rebalance(self):
        state = {'selections':{'2026-08-10':{'picks':['2330']},'2026-09-10':{'picks':[]}}}
        position = position_from_state(state,['2330','2317'],pd.Timestamp('2026-09-10'))
        self.assertEqual(len(position),2)
        self.assertEqual(position.loc['2026-08-10','2330'],.1)
        self.assertEqual(position.loc['2026-09-10'].sum(),0.)

    def test_published_selection_never_recomputed(self):
        calendar = mock.Mock()
        calendar.is_session.return_value = True
        calendar.next_session.return_value = date(2026,11,11)
        calendar.open_at.return_value = datetime(2026,11,11,9,tzinfo=TZ)
        state = {'live_from':'2026-11-10','selections':{'2026-11-10':{'picks':['2330'],'recorded_at':'original'}}}
        original = copy.deepcopy(state)
        with mock.patch('update.data.get_calendar',return_value=calendar), mock.patch('update.data.get') as get:
            append_selection(state,None,None,datetime(2026,11,10,23,tzinfo=TZ))
            get.assert_not_called()
        self.assertEqual(state,original)

    def test_missed_live_decision_cannot_be_backfilled(self):
        calendar = mock.Mock()
        calendar.is_session.return_value = True
        calendar.next_session.return_value = date(2026,11,11)
        calendar.open_at.return_value = datetime(2026,11,11,9,tzinfo=TZ)
        state = {'live_from':'2026-11-10','selections':{}}
        with mock.patch('update.data.get_calendar',return_value=calendar):
            with self.assertRaisesRegex(RuntimeError,'refusing to invent'):
                append_selection(state,None,None,datetime(2026,11,11,10,tzinfo=TZ))
        self.assertEqual(state['selections'],{})

    def test_daytime_run_does_not_create_tonights_decision(self):
        calendar = mock.Mock()
        calendar.is_session.return_value = True
        calendar.next_session.return_value = date(2026,11,11)
        calendar.open_at.return_value = datetime(2026,11,11,9,tzinfo=TZ)
        state = {'live_from':'2026-11-10','selections':{}}
        with mock.patch('update.data.get_calendar',return_value=calendar):
            append_selection(state,None,None,datetime(2026,11,10,12,tzinfo=TZ))
        self.assertEqual(state['selections'],{})
