export const STATIC_AUDIT_SITE = 'https://www.yousafncompany.com';

export const STATIC_LIGHTHOUSE_SCORES = [
  { label: 'Performance', score: 64, tone: 'amber' },
  { label: 'Accessibility', score: 87, tone: 'amber' },
  { label: 'Best Practices', score: 100, tone: 'green' },
  { label: 'SEO', score: 85, tone: 'amber' },
] as const;

export const STATIC_CORE_WEB_VITALS = [
  { label: 'First Contentful Paint', value: '3.0 s' },
  { label: 'Largest Contentful Paint', value: '5.7 s' },
  { label: 'Total Blocking Time', value: '390 ms' },
  { label: 'Cumulative Layout Shift', value: '0' },
  { label: 'Speed Index', value: '3.1 s' },
] as const;

export const STATIC_AUDIT_OPPORTUNITIES = [
  { label: 'Render-blocking requests', detail: 'Est. savings 1,490 ms' },
  { label: 'Font display', detail: 'Est. savings 110 ms' },
  { label: 'LCP request discovery', detail: 'Review priority and preload path' },
  { label: 'Network dependency tree', detail: 'Reduce critical chains' },
  { label: 'Reduce JavaScript execution time', detail: '1.5 s' },
  { label: 'Minimize main-thread work', detail: '4.7 s' },
  { label: 'Color contrast', detail: 'Improve background and foreground contrast' },
  { label: 'Color-only links', detail: 'Add underline or secondary visual cue' },
  { label: 'Touch targets', detail: 'Increase size or spacing' },
  { label: 'Heading order', detail: 'Use sequential heading structure' },
  { label: 'Link text', detail: 'Replace vague Read More link text' },
  { label: 'Canonical', detail: 'Use an absolute canonical URL instead of index.html' },
] as const;

export const STATIC_RESPONSE_HEADERS = [
  { label: 'Status', value: 'HTTP/2 200' },
  { label: 'Server', value: 'Vercel' },
  { label: 'Content-Type', value: 'text/html; charset=utf-8' },
  { label: 'Cache-Control', value: 'public, max-age=0, must-revalidate' },
  { label: 'X-Vercel-Cache', value: 'HIT' },
  { label: 'Strict-Transport-Security', value: 'max-age=63072000' },
] as const;

export const STATIC_AUDIT_AGENT_CONTEXT =
  'CWV/PageSpeed for yousafncompany.com: FCP 3.0s; LCP 5.7s; TBT 390ms; CLS 0; SI 3.1s. Scores P64/A11y87/BP100/SEO85. Fix inputs: render-blocking +1490ms, font display +110ms, LCP discovery, network tree, JS exec 1.5s, main thread 4.7s, contrast, color-only links, touch targets, heading order, vague Read More link, canonical index.html. Headers: HTTP/2 200; Vercel; text/html; cache public max-age=0 must-revalidate; x-vercel-cache HIT; HSTS.';
