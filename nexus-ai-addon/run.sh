#!/usr/bin/env bash

# Exit script if a command returns a non-zero exit code
set -e

# Get options from add-on config
CONFIG_PATH=/data/options.json
LOG_LEVEL=$(jq --raw-output '.log_level // "info"' $CONFIG_PATH)
DATA_DIR=$(jq --raw-output '.data_directory // "/data/nexus"' $CONFIG_PATH)
OPENAI_API_KEY=$(jq --raw-output '.openai_api_key // empty' $CONFIG_PATH)
USE_LOCAL_MODEL=$(jq --raw-output '.use_local_model // false' $CONFIG_PATH)
LOCAL_MODEL_PATH=$(jq --raw-output '.local_model_path // empty' $CONFIG_PATH)
MEMORY_PERSISTENCE=$(jq --raw-output '.memory_persistence // true' $CONFIG_PATH)

# Set environment variables
export LOG_LEVEL="$LOG_LEVEL"
export DATA_DIR="$DATA_DIR"
export OPENAI_API_KEY="$OPENAI_API_KEY"
export USE_LOCAL_MODEL="$USE_LOCAL_MODEL"
export LOCAL_MODEL_PATH="$LOCAL_MODEL_PATH"
export MEMORY_PERSISTENCE="$MEMORY_PERSISTENCE"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nexus"

# Make sure the data directory exists
mkdir -p "$DATA_DIR"

# Initialize PostgreSQL and run database setup
echo "Setting up PostgreSQL database..."
pg_ready=false
while ! $pg_ready; do
  if pg_isready -h localhost -p 5432 -U postgres; then
    pg_ready=true
  else
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
  fi
done

# Create database if it doesn't exist
psql -h localhost -p 5432 -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'nexus'" | grep -q 1 || \
    psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE nexus"

# Create tables if they don't exist
python -m nexus.database.init

# Start the application
echo "Starting Nexus AI..."
exec python -m uvicorn nexus.main:app --host 0.0.0.0 --port 5000
