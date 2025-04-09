#!/usr/bin/with-contenv bashio
# ==============================================================================
# Start Nexus AI service
# ==============================================================================

# Set up paths
export DATA_DIR="/data/nexus"
mkdir -p "${DATA_DIR}"

# Get configuration values
export LOG_LEVEL=$(bashio::config 'log_level')
export OPENAI_API_KEY=$(bashio::config 'openai_api_key')
export USE_LOCAL_MODEL=$(bashio::config 'use_local_model')
export LOCAL_MODEL_PATH=$(bashio::config 'local_model_path')
export MEMORY_PERSISTENCE=$(bashio::config 'memory_persistence')

# Set supervisor token for Home Assistant API access
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"

# Start PostgreSQL
bashio::log.info "Waiting for PostgreSQL to start..."
until pg_isready -h localhost -U postgres; do
    bashio::log.info "PostgreSQL not ready yet..."
    sleep 2
done

# Create database if it doesn't exist
if ! psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw nexus; then
    bashio::log.info "Creating nexus database..."
    psql -h localhost -U postgres -c "CREATE DATABASE nexus"
fi

# Set database URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nexus"

# Initialize database tables
bashio::log.info "Setting up database tables..."
cd /app
python3 -m nexus.database.init

# Start FastAPI server
bashio::log.info "Starting Nexus AI server..."
cd /app
exec python3 -m uvicorn nexus.main:app --host 0.0.0.0 --port 5000
