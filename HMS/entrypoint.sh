#!/bin/bash
# Run database setup (db.create_all() and admin insert)
python -c "from app import init_db; init_db()"
# Start the production web server
gunicorn app:app
