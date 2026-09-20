import type { NextConfig } from "next";

const publicApiBasePath = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1"
).replace(/\/$/, "");

if (!publicApiBasePath.startsWith("/")) {
  throw new Error(
    "NEXT_PUBLIC_API_BASE_URL must be a same-origin path like /api/v1."
  );
}

const backendApiBaseUrl = (
  process.env.BACKEND_API_URL ??
  (process.env.NODE_ENV === "development"
    ? "http://localhost:8000/api/v1"
    : "")
).replace(/\/$/, "");

if (!backendApiBaseUrl) {
  throw new Error(
    "BACKEND_API_URL is required for production frontend builds."
  );
}

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: `${publicApiBasePath}/:path*`,
        destination: `${backendApiBaseUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;