"""Use saved selection dates as 10% rebalance targets for both strategies."""
import pandas as pd
from finlab import FinlabDataFrame


def position_from_state(state, columns, end):
    records = {day:{sid:.1 for sid in row['picks']} for day,row in state['selections'].items() if day <= str(end.date())}
    # Keep explicit empty decisions as cash, and never fill in missing decisions.
    frame = pd.DataFrame(0., index=pd.to_datetime(sorted(records)), columns=columns)
    for day, weights in records.items():
        if weights:
            frame.loc[pd.Timestamp(day), list(weights)] = .1
    assert len(frame) == len(records)
    assert frame.gt(0).sum(axis=1).max() <= 10
    return FinlabDataFrame(frame)
