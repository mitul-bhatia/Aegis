#!/usr/bin/env python3
"""
Aegis Ultimate Demo Server (Minimal Setup)
For testing without full API configuration
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set minimal environment for demo
os.environ.setdefault('MISTRAL_API_KEY', 'demo_key')
os.environ.setdefault('GITHUB_TOKEN', 'demo_token')
os.environ.setdefault('FRONTEND_URL', 'http://localhost:3000')
os.environ.setdefault('BACKEND_URL', 'http://localhost:8000')
os.environ.setdefault('PORT', '8000')

def main():
    print("=" * 60)
    print("🛡️  AEGIS ULTIMATE - Demo Mode")
    print("=" * 60)
    print("⚠️  Running in demo mode with minimal configuration")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("=" * 60)
    
    try:
        # Initialize database
        from database.db import init_db
        init_db()
        print("✅ Database initialized")
        
        # Start server
        from main import app
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 To fix this:")
        print("1. Install dependencies: pip3 install -r requirements.txt")
        print("2. Configure .env file with real API keys")
        print("3. Try again with: python3 run_server.py")

if __name__ == "__main__":
    main()
