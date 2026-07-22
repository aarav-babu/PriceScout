"""Vercel Python serverless entrypoint.

Vercel's @vercel/python runtime detects the module-level ``app`` WSGI callable
and serves it. All routes are rewritten to this function via vercel.json.

Vercel cannot host persistent Redis/Celery processes, so the included
configuration keeps PIPELINE_ENABLED=false and uses the bundled vehicle
fallback. Point DB_* at managed MySQL and set DATA_DIR=/tmp.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402,F401

# Vercel uses this WSGI callable named `app`.
