import type { NextConfig } from "next";

const backendApiBaseUrl = (
  process.env.BACKEND_API_URL ??
  (process.env.NODE_ENV === "development"
    ? "http://localhost:8000/api/v1"
    : "https://c7hi027il3.execute-api.us-east-1.amazonaws.com/api/v1")
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [{
      source: '/api/v1/:path*',
      destination: `${backendApiBaseUrl}/:path*`,
    }];
  },
};

export default nextConfig;
