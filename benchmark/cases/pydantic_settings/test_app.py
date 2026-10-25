from app import load_settings


def test_defaults():
    s = load_settings()
    assert s.app_name == "livefix"
    assert s.retries == 3
