'use client';

import { BrandMark } from '@/components/brand-mark';
import { Button } from '@/components/ui/button';
import { getGoogleLoginUrl } from '@/lib/api/auth';

const capabilities = [
  'Pulls 30 days of Search Console performance',
  'Reads your live page titles, meta and headings',
  'Returns five ranked, evidence-backed fixes',
];

export default function Home() {
  const handleGoogleLogin = () => {
    window.location.href = getGoogleLoginUrl();
  };

  return (
    <div className="flex flex-1 items-center justify-center px-6 py-16">
      <main className="glass flex w-full max-w-md flex-col items-center gap-8 rounded-3xl p-10 sm:p-12">
        <div className="flex flex-col items-center gap-5 text-center">
          <BrandMark className="h-14 w-14" />

          <div className="flex flex-col gap-2">
            <h1 className="text-[1.75rem] font-semibold leading-tight text-slate-900">
              Search Console Agent
            </h1>
            <p className="text-sm leading-relaxed text-slate-600">
              Turn your Search Console data into a ranked list of SEO fixes,
              backed by your own queries and pages.
            </p>
          </div>
        </div>

        <ul className="flex w-full flex-col gap-2.5">
          {capabilities.map((capability) => (
            <li
              key={capability}
              className="flex items-start gap-2.5 text-sm text-slate-700"
            >
              <svg
                viewBox="0 0 20 20"
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600"
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
            className="w-full bg-slate-900 text-white shadow-lg shadow-slate-900/20 transition-colors hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
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
            Authorize with Google
          </Button>

          <p className="text-center text-xs leading-relaxed text-slate-500">
            Read-only access to Search Console. We never post or change anything
            on your site.
          </p>
        </div>
      </main>
    </div>
  );
}
