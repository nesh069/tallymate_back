#!/bin/sh
set -e

# Ensure tables exist for the configured DATABASE_URL (no migrations set up yet).
python -c "
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    db.create_all()
"

exec gunicorn -b 0.0.0.0:5000 run:app
