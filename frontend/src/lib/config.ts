// Keep browser requests same-origin. Next.js rewrites /api/v1 to the private
// deployment target so the API Gateway URL is not embedded in client code.
export const API_BASE_URL = "/api/v1";
