#!/bin/bash
# Build the Aegis sandbox Docker image

echo "🐳 Building Aegis Sandbox Docker Image..."

docker build -f Dockerfile.sandbox -t aegis-sandbox:latest .

if [ $? -eq 0 ]; then
    echo "✅ Sandbox image built successfully!"
    echo "   Image: aegis-sandbox:latest"
    docker images | grep aegis-sandbox
else
    echo "❌ Failed to build sandbox image"
    exit 1
fi
