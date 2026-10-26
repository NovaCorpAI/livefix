"""A tiny service that builds a report about an ICC color profile.

It reads three fields, each from its own module, so a dependency upgrade that
removes those APIs breaks the build in three places at once.
"""

from colorprofile.name import profile_name
from colorprofile.description import profile_description
from colorprofile.rights import profile_rights


def build_report(profile):
    """Return a name, description and copyright report for a color profile."""
    return {
        "name": profile_name(profile),
        "description": profile_description(profile),
        "rights": profile_rights(profile),
    }
