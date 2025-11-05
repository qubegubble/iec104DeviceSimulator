# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies in smaller chunks to reduce memory usage
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install additional build tools in a separate layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    make \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY Datapoints.json .
COPY datapoint.py .
COPY data_simulator.py .
COPY batch_server.py .

# Create a non-root user for security
RUN useradd -m -u 1000 iec104user && \
    chown -R iec104user:iec104user /app

USER iec104user

# Expose the IEC 104 port
EXPOSE 2404

# Health check to ensure the server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('localhost', 2404)); s.close()" || exit 1

# Run the simple IEC 104 server (fallback to complex one if needed)
CMD ["python", "batch_server.py"]