#!/usr/bin/env bashio

set -e

# Get config
export OPENAI_API_KEY=$(bashio::config 'openai_api_key')
export VOICE_ENABLED=$(bashio::config 'voice_enabled')
export GOOGLE_CALENDAR_ENABLED=$(bashio::config 'google_calendar_enabled')
export LOG_LEVEL=$(bashio::config 'log_level' 'info')
export DATA_DIR="/data"

# Create data directories if they don't exist
mkdir -p "$DATA_DIR/db"
mkdir -p "$DATA_DIR/chromadb"
mkdir -p "$DATA_DIR/logs"

# PostgreSQL setup
if bashio::services.available 'postgresql'; then
    bashio::log.info "PostgreSQL service available, configuring..."
    
    # Get PostgreSQL details
    host=$(bashio::services 'postgresql' 'host')
    port=$(bashio::services 'postgresql' 'port')
    username=$(bashio::services 'postgresql' 'username')
    password=$(bashio::services 'postgresql' 'password')
    database="nexus_ai"
    
    # Set environment variable for database connection
    export DATABASE_URL="postgresql://${username}:${password}@${host}:${port}/${database}?sslmode=disable"
    
    # Wait for PostgreSQL service to be ready
    bashio::log.info "Waiting for PostgreSQL service..."
    for i in $(seq 1 30); do
        if pg_isready -h "${host}" -p "${port}" -U "${username}" -d "${database}" -t 1 > /dev/null 2>&1; then
            bashio::log.info "PostgreSQL service is ready"
            break
        fi
        
        if [ "$i" -eq 30 ]; then
            bashio::log.warning "PostgreSQL service not ready after 30 seconds, proceeding anyway..."
        fi
        
        sleep 1
    done

    # Try to create the database if it doesn't exist
    if ! psql -h "${host}" -p "${port}" -U "${username}" -lqt | grep -q "${database}"; then
        bashio::log.info "Creating database ${database}..."
        psql -h "${host}" -p "${port}" -U "${username}" -c "CREATE DATABASE ${database};" || true
    fi
    
    # Set environment variables for SQLAlchemy
    export SQLALCHEMY_DATABASE_URI="$DATABASE_URL"
    export SQLALCHEMY_TRACK_MODIFICATIONS=False
    
    bashio::log.info "PostgreSQL configuration complete"
else
    bashio::log.warning "PostgreSQL service not available, some features may not work correctly"
    # Use SQLite as fallback
    export DATABASE_URL="sqlite:///$DATA_DIR/db/nexus.db"
    export SQLALCHEMY_DATABASE_URI="$DATABASE_URL"
    export SQLALCHEMY_TRACK_MODIFICATIONS=False
fi

# Get Home Assistant API token for connecting back to Home Assistant
export SUPERVISOR_TOKEN=$(bashio::supervisor.token)
export HOME_ASSISTANT_URL="http://supervisor/core"

# Print startup message
bashio::log.info "Starting Nexus AI..."
bashio::log.info "Data directory: $DATA_DIR"
bashio::log.info "Log level: $LOG_LEVEL"

# Start the application
cd /app
exec python3 -m uvicorn nexus.main:app --host 0.0.0.0 --port 5000
