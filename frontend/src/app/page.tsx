'use client';

import { Button } from '@/components/ui/button';
import { getGoogleLoginUrl } from '@/lib/api/auth';

export default function Home() {
  const handleGoogleLogin = () => {
    window.location.href = getGoogleLoginUrl();
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-zinc-50 to-zinc-100 px-6 py-16">
      <main className="flex w-full max-w-md flex-col items-center gap-8 rounded-2xl bg-white p-12 shadow-lg ring-1 ring-zinc-200">
        <div className="flex flex-col items-center gap-3 text-center">
          <h1 className="text-3xl font-bold text-zinc-900">
            Welcome to our SEO Tool
          </h1>
          <p className="text-sm text-zinc-600">
            Analyze your website's performance with Google Search Console insights
          </p>
        </div>

        <Button
          onClick={handleGoogleLogin}
          size="lg"
          className="w-full"
        >
          Please Authorize with Google
        </Button>
      </main>
    </div>
  );
}
