import pandas as pd

from app import add_row


def test_add_row():
    df = pd.DataFrame({"a": [1], "b": [2]})
    out = add_row(df, {"a": 3, "b": 4})
    assert len(out) == 2
    assert out.iloc[1]["a"] == 3
    assert out.iloc[1]["b"] == 4
