"""Vercel Python serverless entrypoint.

Vercel's @vercel/python runtime detects the module-level ``app`` WSGI callable
and serves it. All routes are rewritten to this function via vercel.json.

Note: live Selenium scraping cannot run on Vercel (no browser), so keep
ENABLE_LIVE_SCRAPING unset/false there - the app falls back to the bundled
dataset model. Point DB_* env vars at an external managed MySQL and set
DATA_DIR=/tmp (the only writable path on Vercel).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402,F401

# Vercel uses this WSGI callable named `app`.
