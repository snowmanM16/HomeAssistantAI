FROM python:3.11-slim

WORKDIR /app

# Install required dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create directories for data persistence
RUN mkdir -p /data/nexus

# Copy requirements first to leverage Docker cache
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY nexus/ ./nexus/
COPY run.sh ./run.sh
RUN chmod +x run.sh

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["./run.sh"]
