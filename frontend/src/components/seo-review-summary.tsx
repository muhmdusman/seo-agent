import { REVIEW_LABELS, slugLabel, type SEOReport, type SEOTaskReview } from '@/lib/seo-types';

export function SEOReviewDetails({ review }: { review: SEOTaskReview }) {
  const performance = review.performance;
  const number = (value: number | undefined) => value === undefined ? 'Unavailable' : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  const percent = (value: number | undefined) => value === undefined ? 'Unavailable' : value.toLocaleString(undefined, { style: 'percent', maximumFractionDigits: 2 });

  return <div className="min-w-0 space-y-2 text-sm [overflow-wrap:anywhere]">
    <p className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-zinc-600">
      <span className="font-medium">{REVIEW_LABELS[review.status]}</span>
      <span>Last check <time dateTime={review.checked_at}>{new Date(review.checked_at).toLocaleString()}</time></span>
    </p>
    <p className="whitespace-pre-wrap text-zinc-700">{review.detail}</p>
    {review.url && <p className="text-xs text-zinc-500">{review.url}</p>}
    {review.condition && <dl className="grid grid-cols-[5rem_minmax(0,1fr)] gap-x-3 gap-y-1 text-xs text-zinc-600">
      <dt>Check</dt><dd>{slugLabel(review.condition.field)}</dd>
      <dt>Expected</dt><dd>{review.condition.expected}</dd>
      <dt>Observed</dt><dd>{review.observed_value == null ? 'Unavailable' : Array.isArray(review.observed_value) ? review.observed_value.join('; ') : String(review.observed_value)}</dd>
    </dl>}
    {!!review.changed_fields?.length && <p className="text-xs text-zinc-600">Changed since the previous sample: {review.changed_fields.map(slugLabel).join(', ')}</p>}
    <p className="text-xs font-medium text-zinc-600">Performance: {performance ? slugLabel(performance.status) : 'Not assessed'}</p>
    {performance?.detail && <p className="whitespace-pre-wrap text-xs text-zinc-600">{performance.detail}</p>}
    {performance?.windows && <p className="text-xs text-zinc-500">
      Before: {performance.windows.before.start} to {performance.windows.before.end}<br />
      After: {performance.windows.after.start} to {performance.windows.after.end} (Pacific Time)
    </p>}
    {(performance?.before || performance?.after) && <table className="w-full table-fixed border-collapse text-left text-xs text-zinc-600">
      <caption className="sr-only">Search performance before and after the change</caption>
      <thead><tr className="border-b border-zinc-200">
        <th scope="col" className="w-2/5 py-2 pr-2 font-medium">Metric</th>
        <th scope="col" className="py-2 pr-2 font-medium">Before</th>
        <th scope="col" className="py-2 font-medium">After</th>
      </tr></thead>
      <tbody>
        {([
          ['Clicks', number(performance.before?.clicks), number(performance.after?.clicks)],
          ['Impressions', number(performance.before?.impressions), number(performance.after?.impressions)],
          ['CTR', percent(performance.before?.ctr), percent(performance.after?.ctr)],
          ['Average position', number(performance.before?.position), number(performance.after?.position)],
        ] as const).map(([label, before, after]) => <tr key={label} className="border-b border-zinc-100">
          <th scope="row" className="py-2 pr-2 font-normal">{label}</th>
          <td className="py-2 pr-2 tabular-nums">{before}</td>
          <td className="py-2 tabular-nums">{after}</td>
        </tr>)}
      </tbody>
    </table>}
  </div>;
}

export function SEOReviewSummary({ report }: { report: SEOReport }) {
  const reviews = report.evidence?.reviews ?? [];
  const limitations = report.evidence?.limitations ?? [];
  const taskGeneration = report.evidence?.task_generation;
  if (!reviews.length && !limitations.length && !taskGeneration) return null;

  return <section aria-label="Review summary" className="min-w-0 space-y-3 border-b border-zinc-200 pb-5 [overflow-wrap:anywhere]">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="text-base font-semibold text-zinc-900">Review summary</h2>
      <time dateTime={report.created_at} className="text-xs text-zinc-500">{new Date(report.created_at).toLocaleString()}</time>
    </div>
    <p className="text-xs text-zinc-500">An observed change confirms the checked condition. It does not prove improved rankings or that the change caused a performance difference.</p>
    {taskGeneration && <p className="text-xs text-zinc-600">Task generation: {taskGeneration.created} created from {taskGeneration.candidate} candidate{taskGeneration.candidate === 1 ? '' : 's'}; {taskGeneration.reused} reused and {taskGeneration.already_observed} already observed.</p>}
    {reviews.length > 0 && <ul className="divide-y divide-zinc-200">
      {reviews.map((review, index) => <li key={`${review.task_id}-${index}`} className="space-y-2 py-3">
        <details className="space-y-3">
          <summary className="cursor-pointer text-sm font-medium text-zinc-800">{review.title}
            <span className="mt-1 block text-xs font-normal text-zinc-500">{REVIEW_LABELS[review.status]}</span>
          </summary>
          <SEOReviewDetails review={review} />
        </details>
      </li>)}
    </ul>}
    {limitations.length > 0 && <details className="space-y-2">
      <summary className="cursor-pointer text-xs font-medium text-zinc-600">Review limitations ({limitations.length})</summary>
      <ul className="list-disc space-y-1 pl-4 text-xs text-zinc-600">{limitations.map((detail, index) => <li key={index}>{detail}</li>)}</ul>
    </details>}
  </section>;
}
