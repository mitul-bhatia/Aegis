/** @type {import('next').NextConfig} */
// Robustly parse the API URL from environment variables, ensuring it has https:// and no trailing slash
let rawUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "https://aegis-wpeu.onrender.com";
if (!rawUrl.startsWith("http://") && !rawUrl.startsWith("https://")) {
  rawUrl = "https://" + rawUrl;
}
const apiUrl = rawUrl.replace(/\/$/, "");

const nextConfig = {
  output: "standalone",
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
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

