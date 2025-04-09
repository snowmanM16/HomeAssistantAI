ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.16
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install required system packages and PostgreSQL
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-wheel \
    py3-psycopg2 \
    py3-cryptography \
    py3-aiohttp \
    py3-numpy \
    postgresql \
    postgresql-client \
    postgresql-contrib \
    jq \
    curl

# Create application directory
WORKDIR /app

# Copy application files
COPY nexus/ /app/nexus/
COPY requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

# Copy root filesystem
COPY rootfs /

# Set environment variables
ENV PYTHONPATH="${PYTHONPATH}:/app"
ENV DATA_DIR="/data/nexus"

# S6 will start services defined in /etc/services.d/
ENTRYPOINT ["/init"]
CMD []
