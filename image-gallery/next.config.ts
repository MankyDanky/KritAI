import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ['mongodb'],
  images: {
    domains: ['localhost'],
    unoptimized: true,
  },
};

export default nextConfig;
