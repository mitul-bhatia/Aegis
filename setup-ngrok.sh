#!/bin/bash
# Setup ngrok tunnel for local development

echo "🌐 Setting up ngrok tunnel for Aegis..."
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed"
    echo ""
    echo "Install ngrok:"
    echo "  macOS: brew install ngrok"
    echo "  Or download from: https://ngrok.com/download"
    echo ""
    exit 1
fi

echo "✅ ngrok is installed"
echo ""
echo "Starting ngrok tunnel on port 8000..."
echo "This will create a public URL that forwards to your local backend"
echo ""
echo "⚠️  Keep this terminal open while testing!"
echo ""
echo "Once ngrok starts:"
echo "1. Copy the 'Forwarding' URL (e.g., https://abc123.ngrok.io)"
echo "2. Update BACKEND_URL in .env to that URL"
echo "3. Restart the backend"
echo "4. Try adding the repo again"
echo ""
echo "Press Ctrl+C to stop ngrok when done"
echo ""

ngrok http 8000
