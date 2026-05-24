#!/bin/sh

# 1. Run migrations first thing on container boot
echo "Applying database migrations..."
python manage.py migrate --noinput

# 2. Start Django Q in the background and pipe its logs
echo "Starting Django Q Cluster in the background..."
python manage.py qcluster > /dev/null 2>&1 &

# 3. Start your main web server in the foreground
# (This keeps the container alive)
echo "Starting Gunicorn..."
exec gunicorn AiAdvisor.wsgi:application --bind 0.0.0.0:${PORT:-8000}
