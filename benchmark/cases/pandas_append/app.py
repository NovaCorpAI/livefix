"""Breaks on pandas 2.0+: DataFrame.append was removed."""

import pandas as pd


def add_row(df, row):
    """Return a copy of df with one row (a dict) appended."""
    return df.append(row, ignore_index=True)  # DataFrame.append removed in pandas 2.0
