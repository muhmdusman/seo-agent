import { cn } from '@/lib/utils';

interface BrandMarkProps {
  className?: string;
}

/**
 * The product glyph: a search lens over a rising bar chart.
 *
 * Mirrors app/icon.svg so the tab icon and the in-app mark stay identical. It
 * is decorative wherever a text label sits beside it, hence aria-hidden.
 */
export function BrandMark({ className }: BrandMarkProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-600/25',
        className
      )}
    >
      <svg
        viewBox="0 0 64 64"
        className="h-[58%] w-[58%]"
        fill="none"
        stroke="currentColor"
      >
        <circle cx="28" cy="27" r="13" strokeWidth="4.5" />
        <path
          d="M37.6 36.6 L47.5 46.5"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <g fill="currentColor" stroke="none">
          <rect x="21.5" y="28" width="4" height="6" rx="1.2" />
          <rect x="26" y="23.5" width="4" height="10.5" rx="1.2" />
          <rect x="30.5" y="19.5" width="4" height="14.5" rx="1.2" />
        </g>
      </svg>
    </span>
  );
}
