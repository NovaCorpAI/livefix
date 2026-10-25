import numpy as np

from app import to_floats


def test_to_floats_dtype():
    out = to_floats([1, 2, 3])
    assert out.dtype == np.float64
    assert list(out) == [1.0, 2.0, 3.0]
