import copy
import json
from pathlib import Path
import unittest
import pandas as pd
from dashboard_shared.positions import position_from_state
from dashboard_shared.strategies import CONFIGS

ROOT=Path(__file__).resolve().parents[1]


class ReinvestmentTargets(unittest.TestCase):
    def test_all_saved_dates_and_picks_are_preserved(self):
        for folder in ['strategy2026_pipeline','watch2_pipeline']:
            with self.subTest(strategy=folder):
                state=json.loads((ROOT/folder/'selections.json').read_text(encoding='utf-8'))
                before=copy.deepcopy(state)
                columns=sorted({sid for row in state['selections'].values() for sid in row['picks']})
                end=pd.Timestamp(max(state['selections']))
                position=position_from_state(state,columns,end)
                self.assertEqual(position.index.tolist(),list(pd.to_datetime(sorted(state['selections']))))
                for day,row in state['selections'].items():
                    weights=position.loc[day]
                    self.assertEqual(set(weights.index[weights.gt(0)]),set(row['picks']))
                    self.assertTrue(weights[weights.gt(0)].eq(.1).all())
                self.assertEqual(state,before)

    def test_missing_month_is_not_invented_and_second_decision_is_not_dropped(self):
        state={'selections':{
            '2026-06-10':{'picks':['A']},
            '2026-08-10':{'picks':['A','B']},
            '2026-08-12':{'picks':['B']},
            '2026-09-10':{'picks':['C']}}}
        position=position_from_state(state,['A','B','C'],pd.Timestamp('2026-08-31'))
        self.assertEqual(len(position),3)
        self.assertAlmostEqual(position.loc['2026-08-10'].sum(),.2)
        self.assertEqual(position.loc['2026-08-12','A'],0.)
        self.assertEqual(position.loc['2026-08-12','B'],.1)

    def test_both_pages_use_current_assets_and_keep_their_fees(self):
        two,six=CONFIGS['2026']['allocation'],CONFIGS['watch2']['allocation']
        for key in ['mode','capital_label','weight','budget_includes_fee']:
            self.assertEqual(two[key],six[key])
        self.assertEqual(two['mode'],'rebalance')
        self.assertEqual(two['fee_buy'],.001425)
        self.assertEqual(two['fee_sell'],.001425)
        self.assertTrue(CONFIGS['2026']['has_native_report'])
