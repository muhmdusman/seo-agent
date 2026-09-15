const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

// Keep browser requests same-origin. Next.js rewrites this path to the private
// deployment target so auth cookies belong to the frontend domain.
export const API_BASE_URL = (configuredApiBaseUrl || "/api/v1").replace(/\/$/, "");
