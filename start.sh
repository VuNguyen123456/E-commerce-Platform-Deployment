#!/bin/bash

# Startup script for checkout service
set -e

echo "Starting checkout service..."

# Wait for database to be ready (optional)
echo "Checking database connectivity..."
python -c "
import os
import psycopg2
import time
import sys

max_retries = 10
retry_count = 0

while retry_count < max_retries:
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            database=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            connect_timeout=10
        )
        conn.close()
        print('Database connection successful!')
        break
    except Exception as e:
        retry_count += 1
        print(f'Database connection failed (attempt {retry_count}/{max_retries}): {e}')
        if retry_count >= max_retries:
            print('Could not connect to database after maximum retries')
            sys.exit(1)
        time.sleep(2)
"

echo "Database is ready. Starting Gunicorn..."

# Start gunicorn with configuration
exec gunicorn --config gunicorn.conf.py checkout_service:app