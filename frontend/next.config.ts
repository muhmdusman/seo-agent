import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Only use rewrites in production (when deployed to Amplify)
    // In local development, the API_BASE_URL from .env.local is used directly
    const isProduction = process.env.NODE_ENV === 'production';
    
    if (isProduction) {
      return [
        {
          source: '/api/v1/:path*',
          destination: 'http://search-console-prod.eba-auaxqesy.us-east-1.elasticbeanstalk.com/api/v1/:path*',
        },
      ];
    }
    
    return [];
  },
};

export default nextConfig;
