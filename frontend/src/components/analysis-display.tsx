'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface AnalysisDisplayProps {
  siteUrl: string;
  analysis: string;
}

export function AnalysisDisplay({ siteUrl, analysis }: AnalysisDisplayProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>SEO Analysis for {siteUrl}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-800">
          {analysis}
        </div>
      </CardContent>
    </Card>
  );
}
