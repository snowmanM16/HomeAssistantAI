ARG BUILD_FROM
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    git \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev

# Set working directory
WORKDIR /opt/nexus-ai

# Copy application files
COPY . /opt/nexus-ai/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Make run script executable
RUN chmod a+x /opt/nexus-ai/run.sh

# Set the entrypoint
ENTRYPOINT [ "/opt/nexus-ai/run.sh" ]

# Labels
LABEL \
    io.hass.name="Nexus AI" \
    io.hass.description="Intelligent AI assistant with memory and smart home control" \
    io.hass.type="addon" \
    io.hass.version="0.1.0" \
    maintainer="Your Name <your.email@example.com>"