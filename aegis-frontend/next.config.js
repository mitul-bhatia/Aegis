/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // Environment variables
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'https://aegis-backend-kiw7.onrender.com',
    NEXT_PUBLIC_GITHUB_CLIENT_ID: process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || process.env.GITHUB_CLIENT_ID || 'Ov23li7vdknIS2ZtxxOH',
  },
  
  // Rewrites to proxy API requests directly to backend, avoiding CORS and cross-domain cookie issues
  async rewrites() {
    let backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'https://aegis-backend-kiw7.onrender.com';
    if (!backendUrl.startsWith('http')) {
      backendUrl = `https://${backendUrl}`;
    }
    const cleanUrl = backendUrl.replace(/\/$/, '');
    return [
      {
        source: '/api/v1/:path*',
        destination: `${cleanUrl}/api/v1/:path*`,
      },
      {
        source: '/webhook/:path*',
        destination: `${cleanUrl}/webhook/:path*`,
      },
      {
        source: '/health',
        destination: `${cleanUrl}/health`,
      },
    ];
  },
  
  // Vercel-specific optimizations
  experimental: {
    optimizeCss: true,
  },
  
  // Image optimization
  images: {
    domains: ['avatars.githubusercontent.com'],
  },
  
  // Disable x-powered-by header
  poweredByHeader: false,
  
  // Compression
  compress: true,
  
  // React strict mode
  reactStrictMode: true,
}

module.exports = nextConfig
