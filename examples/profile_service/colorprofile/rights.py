"""Read an ICC color profile's copyright string.

Written against Pillow 12, where ImageCmsProfile exposed a `product_copyright`
attribute. Pillow 13.0.0 (the security release for CVE-2026-112398) removed it.
"""

from PIL import ImageCms


def profile_rights(profile):
    """Return the profile's copyright string, trimmed."""
    return profile.product_copyright.strip()
