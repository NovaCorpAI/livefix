"""Read an ICC color profile's human-readable name.

Written against Pillow 12, where ImageCmsProfile exposed a `product_name`
attribute. Pillow 13.0.0 (the security release for CVE-2026-112398) removed it.
"""

from PIL import ImageCms


def profile_name(profile):
    """Return the profile's name, trimmed."""
    return ImageCms.getProfileName(profile).strip()
