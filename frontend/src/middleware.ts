import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js middleware for route protection based on authentication state.
 *
 * This middleware:
 * - Protects the /dashboard route by requiring authentication
 * - Redirects unauthenticated users from /dashboard to /
 * - Redirects authenticated users from / to /dashboard
 *
 * The backend sets httpOnly `access_token` / `refresh_token` cookies. The
 * refresh_token is long-lived, so the presence of either cookie means the
 * user is authenticated.
 */
export function middleware(request: NextRequest) {
  const authed = Boolean(
    request.cookies.get('access_token') || request.cookies.get('refresh_token')
  );
  const { pathname } = request.nextUrl;

  // Protect /dashboard route - redirect unauthenticated users to landing page
  if (pathname.startsWith('/dashboard') && !authed) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Redirect authenticated users away from landing page to dashboard
  if (pathname === '/' && authed) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Allow the request to proceed
  return NextResponse.next();
}

/**
 * Configure which routes the middleware should run on.
 * Matches:
 * - / (landing page)
 * - /dashboard and all sub-routes (/dashboard/*)
 */
export const config = {
  matcher: ['/', '/dashboard/:path*'],
};
