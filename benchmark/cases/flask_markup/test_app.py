from app import bold


def test_bold_escapes():
    out = str(bold("a<b"))
    assert out == "<b>a&lt;b</b>"
