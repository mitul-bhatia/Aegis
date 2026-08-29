/** @type {import('next').NextConfig} */
// Backend URL is fixed infrastructure — the proxy target does not change per-environment.
// NEXT_PUBLIC_API_URL is still read at runtime in lib/api.ts for direct client-side calls.
const BACKEND_URL = "https://aegis-wpeu.onrender.com";

const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

