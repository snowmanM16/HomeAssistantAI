ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Python and dependencies
RUN apk add --no-cache \
        python3 \
        py3-pip \
        py3-wheel \
        py3-setuptools \
        py3-numpy \
        py3-scikit-learn \
        py3-pandas \
        postgresql-client \
        postgresql-dev \
        gcc \
        g++ \
        musl-dev \
        jq \
        curl

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY nexus/ /app/nexus/
COPY run.sh /

# Make executable
RUN chmod a+x /run.sh

# Set entrypoint
ENTRYPOINT [ "/run.sh" ]

# Labels
LABEL \
    io.hass.name="Nexus AI" \
    io.hass.description="Intelligent AI assistant with memory and smart home control" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="Your Name <your.email@example.com>"
