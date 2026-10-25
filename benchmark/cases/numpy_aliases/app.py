"""Breaks on NumPy 1.24+: the np.float alias was removed."""

import numpy as np


def to_floats(values):
    """Return the values as a float64 array."""
    return np.array(values).astype(np.float)  # np.float removed in NumPy 1.24
