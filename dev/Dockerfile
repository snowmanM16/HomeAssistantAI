FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the application
COPY nexus-ai-addon/nexus /app/nexus
COPY nexus-ai-addon/requirements.txt /app/

# Copy development files
COPY dev/run-dev.sh /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a data directory
RUN mkdir -p /data/nexus

# Make scripts executable
RUN chmod +x /app/run-dev.sh

# Set environment variables
ENV PYTHONPATH="/app"
ENV DATA_DIR="/data/nexus"
ENV DATABASE_URL="sqlite:////data/nexus/database.sqlite"
ENV PORT=5000

# Expose port
EXPOSE 5000

# Run the development server
CMD ["/app/run-dev.sh"]