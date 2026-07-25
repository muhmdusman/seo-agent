import { Suspense } from "react";

import { CallbackStatus } from "@/components/site-connect/CallbackStatus";

export default function CallbackPage() {
  return (
    <div className="flex flex-1 items-center justify-center px-6 py-16">
      <main className="glass w-full max-w-lg rounded-3xl p-8 text-center sm:p-10">
        <Suspense
          fallback={<p className="text-sm text-slate-500">Loading...</p>}
        >
          <CallbackStatus />
        </Suspense>
      </main>
    </div>
  );
}
