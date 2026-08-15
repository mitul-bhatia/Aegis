import re

with open("aegis-frontend/next.config.js", "r") as f:
    content = f.read()

new_env = """  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'https://aegis-backend-kiw7.onrender.com',
    NEXT_PUBLIC_GITHUB_CLIENT_ID: process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || process.env.GITHUB_CLIENT_ID || 'Ov23li7vdknIS2ZtxxOH',
    NEXT_PUBLIC_GITHUB_APP_NAME: process.env.NEXT_PUBLIC_GITHUB_APP_NAME || 'aegis-security',
  },"""

content = re.sub(r"  env: \{.*?\},", new_env, content, flags=re.DOTALL)

with open("aegis-frontend/next.config.js", "w") as f:
    f.write(content)
