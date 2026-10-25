"""LiveFix: a web-grounded agent that repairs broken code against moving APIs.

It runs a failing test, reads the traceback, searches the live web (Tavily) for
the current migration or fix, asks an NVIDIA Nemotron model on Nebius Token
Factory to rewrite the offending file, applies the change, and re-runs until the
test passes. The web step is what lets it fix breakages that post-date the
model's training cutoff.
"""

__version__ = "0.1.0"
