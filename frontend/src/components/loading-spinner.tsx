interface LoadingSpinnerProps {
  text?: string;
}

export function LoadingSpinner({ text = 'Loading...' }: LoadingSpinnerProps) {
  return (
    <div
      // The analysis takes tens of seconds, so the status text is announced to
      // screen readers as the backend reports each stage.
      role="status"
      aria-live="polite"
      className="glass flex flex-col items-center justify-center gap-4 rounded-2xl px-6 py-12"
    >
      <span className="relative flex h-10 w-10 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-indigo-500/20" />
        <span className="h-10 w-10 animate-spin rounded-full border-[3px] border-slate-200 border-t-indigo-600" />
      </span>

      <div className="flex flex-col items-center gap-1 text-center">
        <p className="text-sm font-medium text-slate-900">{text}</p>
        <p className="text-xs text-slate-500">
          This usually takes under a minute.
        </p>
      </div>
    </div>
  );
}
