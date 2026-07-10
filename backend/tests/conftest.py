"""
conftest.py — ensure the backend/ directory is on sys.path so that
`import database`, `import main`, etc. work when pytest is invoked
from the project root with `pytest backend/tests/`.
"""
import sys
import os
from hypothesis import settings, HealthCheck

# Insert the backend/ directory at the front of sys.path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

# Register a "ci" profile with reduced examples for fast checkpoint runs.
# The default profile (100 examples) is kept for thorough local runs.
settings.register_profile(
    "ci",
    max_examples=25,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
# Activate the ci profile when HYPOTHESIS_PROFILE=ci is set, otherwise use default.
_profile = os.getenv("HYPOTHESIS_PROFILE", "default")
settings.load_profile(_profile)
