"""Breaks on Python 3.10+: collections.Mapping was removed."""

from collections import Mapping  # removed in Python 3.10, use collections.abc


def count_keys(m):
    if not isinstance(m, Mapping):
        raise TypeError("expected a mapping")
    return len(m)
