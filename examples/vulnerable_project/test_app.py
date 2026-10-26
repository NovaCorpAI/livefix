from PIL import ImageCms

from app import profile_label


def test_profile_label_returns_name():
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    label = profile_label(profile)
    assert isinstance(label, str) and label, "expected a non-empty profile name"
    assert "sRGB" in label
