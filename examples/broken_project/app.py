"""A small module that broke when it moved to a newer Python.

`collections.Mapping` was deprecated for years and removed in Python 3.10;
the correct import is now `collections.abc.Mapping`. This is exactly the kind
of post-cutoff, documented migration LiveFix is meant to find and apply.
"""

from collections import Mapping  # broken on Python 3.10+


def count_keys(m):
    if not isinstance(m, Mapping):
        raise TypeError("expected a mapping")
    return len(m)
