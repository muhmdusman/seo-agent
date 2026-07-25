'use client';

import type { ComponentPropsWithoutRef } from 'react';
import Markdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { Card, CardContent, CardHeader } from '@/components/ui/card';

interface AnalysisDisplayProps {
  siteUrl: string;
  analysis: string;
}

/**
 * Element styling for the model's markdown.
 *
 * react-markdown renders semantic HTML but ships no styles, so every tag the
 * model can emit needs an entry here. Anything left out falls back to the
 * browser default, which reads as unstyled next to the rest of the dashboard.
 */
const markdownComponents: Components = {
  // The card already owns the page's h1, so the model's headings start one
  // level down to keep the document outline valid for screen readers.
  h1: ({ children }) => (
    <h2 className="mt-9 border-b border-slate-200/80 pb-2.5 text-lg font-semibold text-slate-900 first:mt-0">
      {children}
    </h2>
  ),

  h2: ({ children }) => (
    <h3 className="mt-9 text-base font-semibold text-slate-900 first:mt-0">
      {children}
    </h3>
  ),

  h3: ({ children }) => (
    <h4 className="mt-7 flex items-baseline gap-2 text-[0.9375rem] font-semibold text-slate-900 first:mt-0">
      {children}
    </h4>
  ),

  h4: ({ children }) => (
    <h5 className="mt-6 text-sm font-semibold text-slate-800 first:mt-0">
      {children}
    </h5>
  ),

  p: ({ children }) => (
    <p className="text-sm leading-relaxed text-slate-600">{children}</p>
  ),

  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),

  em: ({ children }) => <em className="italic text-slate-700">{children}</em>,

  ul: ({ children }) => (
    <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-slate-600 marker:text-indigo-400">
      {children}
    </ul>
  ),

  ol: ({ children }) => (
    <ol className="list-decimal space-y-1.5 pl-5 text-sm leading-relaxed text-slate-600 marker:font-medium marker:text-indigo-500">
      {children}
    </ol>
  ),

  // Nested lists need tightening, otherwise the outer space-y stacks with the
  // inner one and the hierarchy stops reading as a hierarchy.
  li: ({ children }) => (
    <li className="[&>ol]:mt-1.5 [&>ul]:mt-1.5">{children}</li>
  ),

  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-indigo-700 underline decoration-indigo-300 underline-offset-2 transition-colors hover:text-indigo-900 hover:decoration-indigo-500"
    >
      {children}
    </a>
  ),

  code: ({ children }) => (
    <code className="rounded-md border border-slate-200/80 bg-slate-100/80 px-1.5 py-0.5 font-mono text-[0.8125rem] text-slate-800">
      {children}
    </code>
  ),

  // The descendant selectors undo the inline-pill styling above, since a fenced
  // block arrives as <pre><code>.
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-xl bg-slate-900 p-4 text-xs leading-relaxed text-slate-100 [&_code]:border-0 [&_code]:bg-transparent [&_code]:p-0 [&_code]:text-inherit">
      {children}
    </pre>
  ),

  blockquote: ({ children }) => (
    <blockquote className="rounded-r-lg border-l-2 border-indigo-300 bg-indigo-50/40 py-2 pl-4 pr-3 text-sm italic text-slate-600">
      {children}
    </blockquote>
  ),

  hr: () => <hr className="border-slate-200/80" />,

  // Tables come from remark-gfm. The wrapper keeps a wide pricing table from
  // widening the whole card on small screens.
  table: ({ children }: ComponentPropsWithoutRef<'table'>) => (
    <div className="overflow-x-auto rounded-xl border border-slate-200/80">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),

  th: ({ children }) => (
    <th className="border-b border-slate-200/80 bg-slate-50/80 px-3.5 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
      {children}
    </th>
  ),

  td: ({ children }) => (
    <td className="border-b border-slate-100 px-3.5 py-2.5 align-top text-slate-600">
      {children}
    </td>
  ),

  del: ({ children }) => (
    <del className="text-slate-400 line-through">{children}</del>
  ),
};

export function AnalysisDisplay({ siteUrl, analysis }: AnalysisDisplayProps) {
  return (
    <Card>
      <CardHeader className="gap-1 border-b border-slate-200/70 pb-4">
        <p className="text-xs font-medium uppercase tracking-wide text-indigo-600">
          SEO analysis
        </p>
        <h2 className="break-all text-base font-semibold text-slate-900">
          {siteUrl}
        </h2>
      </CardHeader>

      <CardContent className="pt-6">
        <div className="flex flex-col gap-3">
          <Markdown
            remarkPlugins={[remarkGfm]}
            components={markdownComponents}
          >
            {analysis}
          </Markdown>
        </div>
      </CardContent>
    </Card>
  );
}
