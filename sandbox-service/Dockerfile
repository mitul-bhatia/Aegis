FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI (to communicate with Docker daemon)
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Expose port
EXPOSE 8080

# Run the service
CMD ["python", "main.py"]
