'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BrandMark } from '@/components/brand-mark';
import { Button } from '@/components/ui/button';
import { getGoogleLoginUrl } from '@/lib/api/auth';
import { getCurrentUserId } from '@/lib/auth';

const capabilities = [
  'Pulls 30 days of Search Console performance',
  'Reads your live page titles, meta and headings',
  'Returns five ranked, evidence-backed fixes',
  'Tailored recommendations based on your goals',
];

export default function Home() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // Check if user already has valid token
    const checkAuth = async () => {
      try {
        const userId = await getCurrentUserId();
        if (userId) {
          console.log('✅ User already authenticated, redirecting to dashboard');
          router.push('/dashboard');
          return;
        }
      } catch (error) {
        console.log('❌ No valid token, showing login page');
      } finally {
        setIsChecking(false);
      }
    };

    checkAuth();
  }, [router]);

  const handleGoogleLogin = () => {
    window.location.href = getGoogleLoginUrl();
  };

  // Show loading state while checking authentication
  if (isChecking) {
    return (
      <div className="flex flex-1 items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="flex flex-col items-center gap-4">
          <span className="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-700 border-t-indigo-500" />
          <p className="text-sm text-slate-400">Checking authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6 py-16 min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <main className="backdrop-blur-xl bg-slate-800/50 border border-slate-700/50 flex w-full max-w-md flex-col items-center gap-8 rounded-3xl p-10 sm:p-12 shadow-2xl">
        <div className="flex flex-col items-center gap-5 text-center">
          <div className="relative">
            <div className="absolute inset-0 blur-2xl bg-gradient-to-r from-indigo-500 to-purple-500 opacity-20 rounded-full"></div>
            <BrandMark className="h-16 w-16 relative z-10" />
          </div>

          <div className="flex flex-col gap-2">
            <h1 className="text-[2rem] font-bold leading-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Search Console Agent
            </h1>
            <p className="text-sm leading-relaxed text-slate-300">
              Turn your Search Console data into a ranked list of SEO fixes,
              backed by your own queries and pages.
            </p>
          </div>
        </div>

        <ul className="flex w-full flex-col gap-3">
          {capabilities.map((capability) => (
            <li
              key={capability}
              className="flex items-start gap-3 text-sm text-slate-200"
            >
              <svg
                viewBox="0 0 20 20"
                aria-hidden="true"
                className="mt-0.5 h-5 w-5 shrink-0 text-indigo-400"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.86-9.47a.75.75 0 0 0-1.22-.86l-3.24 4.53-1.62-1.62a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.1l3.75-5.25Z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="leading-relaxed">{capability}</span>
            </li>
          ))}
        </ul>

        <div className="flex w-full flex-col gap-3">
          <Button
            onClick={handleGoogleLogin}
            size="lg"
            className="group relative w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold shadow-lg hover:shadow-indigo-500/50 transition-all duration-300 hover:scale-[1.02]"
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
              className="h-[18px] w-[18px]"
            >
              <path
                fill="#4285F4"
                d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.46a5.53 5.53 0 0 1-2.4 3.63v3.01h3.88c2.27-2.09 3.58-5.17 3.58-8.83Z"
              />
              <path
                fill="#34A853"
                d="M12 24c3.24 0 5.96-1.08 7.94-2.9l-3.88-3.01c-1.08.72-2.45 1.15-4.06 1.15-3.13 0-5.78-2.11-6.72-4.96H1.29v3.12A11.99 11.99 0 0 0 12 24Z"
              />
              <path
                fill="#FBBC05"
                d="M5.28 14.28a7.2 7.2 0 0 1 0-4.56V6.6H1.29a12 12 0 0 0 0 10.8l3.99-3.12Z"
              />
              <path
                fill="#EA4335"
                d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.44-3.44C17.95 1.19 15.23 0 12 0 7.31 0 3.26 2.69 1.29 6.6l3.99 3.12C6.22 6.86 8.87 4.75 12 4.75Z"
              />
            </svg>
            <span className="relative z-10">Authorize with Google</span>
            <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-indigo-400 to-purple-400 opacity-0 group-hover:opacity-20 transition-opacity duration-300" />
          </Button>

          <p className="text-center text-xs leading-relaxed text-slate-400">
            Read-only access to Search Console. We never post or change anything
            on your site.
          </p>
        </div>
      </main>
    </div>
  );
}
