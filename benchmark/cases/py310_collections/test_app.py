from app import count_keys


def test_count_keys():
    assert count_keys({"a": 1, "b": 2}) == 2


def test_rejects_non_mapping():
    try:
        count_keys([1, 2, 3])
    except TypeError:
        return
    raise AssertionError("expected TypeError for a non-mapping")
