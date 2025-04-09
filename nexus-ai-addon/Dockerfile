ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup base
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-psycopg2 \
    py3-cryptography \
    py3-aiohttp \
    py3-numpy \
    postgresql-client

# Copy app
WORKDIR /app
COPY . /app

# Install requirements
RUN pip3 install --no-cache-dir -r requirements.txt

# Create data directory
RUN mkdir -p /data

# S6-Overlay setup
RUN chmod +x run.sh

# Copy root filesystem
COPY rootfs /

WORKDIR /app

# Set environment variables
ENV PYTHONPATH="${PYTHONPATH}:/app"
ENV DATA_DIR="/data"

CMD [ "./run.sh" ]
