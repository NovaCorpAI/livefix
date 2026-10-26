from PIL import ImageCms

from service import build_report


def test_build_report_has_all_fields():
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    report = build_report(profile)
    assert set(report) == {"name", "description", "rights"}
    assert all(isinstance(v, str) for v in report.values())
    # sRGB's built-in profile fills all three, so none should be empty.
    assert report["name"]
    assert report["description"]
    assert report["rights"]
