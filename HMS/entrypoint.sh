#!/bin/bash
# Run database setup (db.create_all() and admin insert)
python -c "from app import setup_database; setup_database()"
# Start the production web server
gunicorn app:app
