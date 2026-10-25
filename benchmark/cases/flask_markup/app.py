"""Breaks on Flask 3.1+: the Markup re-export was removed from flask."""

from flask import Markup  # removed from the flask namespace in Flask 3.1


def bold(text):
    """Return bold HTML with the text safely escaped."""
    return Markup("<b>{}</b>").format(text)
