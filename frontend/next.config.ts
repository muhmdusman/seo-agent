import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://search-console-prod.eba-auaxqesy.us-east-1.elasticbeanstalk.com/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;
