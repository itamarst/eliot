"""
Tests for the eliot package.
"""

# Increase hypothesis deadline so we don't time out on PyPy:
from hypothesis import settings
settings.register_profile("eliot", deadline=1000)
settings.load_profile("eliot")
