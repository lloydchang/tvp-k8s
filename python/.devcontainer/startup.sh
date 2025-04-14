#!/bin/bash

# Script to start the TVP API as a background service when the dev container starts
echo "Setting up TVP API service..."

# Create directory for log files
mkdir -p /var/log/tvp-api

# Install supervisor if not already installed
if ! command -v supervisord &> /dev/null; then
    echo "Installing supervisor..."
    apt-get update && apt-get install -y supervisor
fi

# Create supervisor config for the TVP API
cat > /etc/supervisor/conf.d/tvp-api.conf << EOF
[program:tvp-api]
command=/workspaces/tvp/python/run-all-api-services.sh
directory=/workspaces/tvp/python
autostart=true
autorestart=true
startretries=3
stderr_logfile=/var/log/tvp-api/error.log
stdout_logfile=/var/log/tvp-api/output.log
environment=PYTHONPATH=/workspaces/tvp/python:.,ENVIRONMENT=development,VERIFY_SSL=false
stopsignal=TERM
stopasgroup=true
killasgroup=true
EOF

# Make sure supervisor daemon is running before using supervisorctl
if ! pgrep -f "supervisord" > /dev/null; then
    echo "Starting supervisord daemon..."
    supervisord -c /etc/supervisor/supervisord.conf
    sleep 2  # Give it a moment to initialize
fi

# Now reload config and restart the service
echo "Updating supervisor configuration..."
supervisorctl update
echo "Starting TVP API service..."
supervisorctl restart tvp-api

echo "TVP API service has been started"
echo "Check logs with: supervisorctl tail -f tvp-api"
echo "Control service with: supervisorctl {status|stop|restart} tvp-api"