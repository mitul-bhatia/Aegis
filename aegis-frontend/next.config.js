/** @type {import('next').NextConfig} */
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
        destination: "https://aegis-backend-kiw7.onrender.com/api/v1/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
