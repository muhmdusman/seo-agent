import { Suspense } from "react";

import { CallbackStatus } from "@/components/site-connect/CallbackStatus";

export default function CallbackPage() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 px-6 py-16">
      <main className="w-full max-w-lg rounded-2xl bg-white p-8 text-center shadow-sm ring-1 ring-zinc-200 sm:p-10">
        <Suspense fallback={<p className="text-sm text-zinc-500">Loading...</p>}>
          <CallbackStatus />
        </Suspense>
      </main>
    </div>
  );
}
