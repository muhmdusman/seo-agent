import Image from 'next/image';
import { cn } from '@/lib/utils';

interface BrandMarkProps {
  className?: string;
}

export function BrandMark({ className }: BrandMarkProps) {
  return (
    <Image
      src="/logo.png"
      alt="SEO Agent"
      width={250}
      height={100}
      className={cn('h-10 w-auto object-contain', className)}
      priority
    />
  );
}
