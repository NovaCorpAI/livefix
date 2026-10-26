"""Reads the human-readable name of an ICC color profile.

Written against Pillow 12, where ImageCmsProfile exposed a `product_name`
attribute. Pillow 13.0.0 removed it, so this raises AttributeError once the
project upgrades to the security release.
"""

from PIL import ImageCms


def profile_label(profile):
    """Return the profile's human-readable name, trimmed."""
    return profile.product_name.strip()
