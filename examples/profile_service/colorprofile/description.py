"""Read an ICC color profile's description.

Written against Pillow 12, where ImageCmsProfile exposed a `product_desc`
attribute. Pillow 13.0.0 (the security release for CVE-2026-112398) removed it.
"""

from PIL import ImageCms


def profile_description(profile):
    """Return the profile's description, trimmed."""
    return profile.product_desc.strip()
