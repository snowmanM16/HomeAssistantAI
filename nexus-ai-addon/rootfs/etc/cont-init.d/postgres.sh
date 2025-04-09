#!/usr/bin/with-contenv bashio
# ==============================================================================
# Initialize PostgreSQL
# ==============================================================================
declare postgres_data
bashio::log.info "Initializing PostgreSQL..."

# Get the location of the data store
postgres_data="/data/postgres"
mkdir -p "${postgres_data}"

# Initialize data directory if it is empty
if ! bashio::fs.directory_exists "${postgres_data}/pg_hba.conf"; then
    bashio::log.info "Initializing PostgreSQL data directory..."
    mkdir -p "${postgres_data}"
    chown -R postgres:postgres "${postgres_data}"
    su - postgres -c "initdb -D ${postgres_data}"
fi

# Modify the PostgreSQL configuration
bashio::log.info "Configuring PostgreSQL..."
sed -i "s|data_directory = '.*'|data_directory = '${postgres_data}'|g" \
    "${postgres_data}/postgresql.conf"
    
sed -i "s|#listen_addresses = '.*'|listen_addresses = '127.0.0.1'|g" \
    "${postgres_data}/postgresql.conf"

# Ensure the run directory exists
mkdir -p /var/run/postgresql
chown postgres:postgres /var/run/postgresql
