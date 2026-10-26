"""A small image utility that reads an ICC color profile's name.
Written against Pillow 12, where ImageCmsProfile exposed a `product_name`
attribute. Pillow 13.0.0 (the security release for CVE-2026-112398) removed it,
so once the project upgrades to patch the CVE this raises AttributeError.
"""

from PIL import ImageCms

def profile_label(profile):
    """Return the profile's human-readable name, trimmed."""
    return ImageCms.getProfileName(profile).strip()
