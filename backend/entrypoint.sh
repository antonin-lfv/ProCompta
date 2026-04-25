#!/bin/sh
set -e
tailwindcss -c /app/tailwind.config.js \
    -i /app/app/static/css/input.css \
    -o /app/app/static/css/tailwind.css \
    --minify 2>&1 | grep -v "Browserslist"
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
