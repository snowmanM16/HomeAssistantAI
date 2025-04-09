#!/usr/bin/with-contenv bashio
# ==============================================================================
# Set up PostgreSQL
# ==============================================================================

bashio::log.info "Setting up PostgreSQL environment..."

# Create data directory
mkdir -p /data/postgres
chown -R postgres:postgres /data/postgres

# Create application data directory
mkdir -p /data/nexus
chown -R root:root /data/nexus

# Ensure PostgreSQL run directory exists
mkdir -p /var/run/postgresql
chown postgres:postgres /var/run/postgresql
