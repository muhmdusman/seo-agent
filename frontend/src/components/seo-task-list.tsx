'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCheck } from 'lucide-react';
import { STAGE_LABELS, type SEOTask } from '@/lib/seo-types';

interface Props {
  tasks: SEOTask[];
  disabled: boolean;
  onChange: (task: SEOTask, completed: boolean, subtaskId?: string) => Promise<void>;
}

export function SEOTaskList({ tasks, disabled, onChange }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const pending = tasks.filter(task => !task.completed_at);
  const completed = tasks.filter(task => task.completed_at);
  const openId = expanded === '' ? '' : pending.some(task => task.id === expanded) ? expanded : pending[0]?.id;

  function taskRow(task: SEOTask, isCompleted = false) {
    const isOpen = isCompleted ? expanded === task.id : openId === task.id;
    const done = task.subtasks.filter(subtask => subtask.completed_at).length;
    return (
      <div key={task.id} className="border-b border-zinc-200 py-3">
        <div className="flex items-start gap-3">
          <input type="checkbox" checked={!!task.completed_at} disabled={disabled}
            onChange={event => void onChange(task, event.target.checked)}
            aria-label={`${isCompleted ? 'Reopen' : 'Complete'} ${task.title}`}
            className="mt-1 h-4 w-4 shrink-0 accent-emerald-700 disabled:opacity-40" />
          <button type="button" aria-expanded={isOpen} aria-controls={`task-${task.id}`}
            onClick={() => setExpanded(isOpen ? '' : task.id)} className="flex min-w-0 flex-1 items-start gap-2 text-left">
            <span className="min-w-0 flex-1">
              <span className={`block break-words text-sm font-medium ${isCompleted ? 'text-zinc-500 line-through' : 'text-zinc-900'}`}>{task.title}</span>
              <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500">
                <span className={task.priority === 'critical' ? 'text-red-700' : task.priority === 'high' ? 'text-amber-700' : 'text-zinc-500'}>{task.priority.replace('-', ' ')}</span>
                <span>{done}/{task.subtasks.length} steps</span>
              </span>
            </span>
            {isOpen ? <ChevronDown className="mt-0.5 h-4 w-4 shrink-0" /> : <ChevronRight className="mt-0.5 h-4 w-4 shrink-0" />}
          </button>
        </div>
        {isOpen && <div id={`task-${task.id}`} className="ml-7 mt-4 space-y-4 text-sm [overflow-wrap:anywhere]">
          <p className="text-xs text-zinc-500">{task.scope}</p>
          <div><h4 className="font-medium text-zinc-800">Finding</h4><p className="mt-1 whitespace-pre-wrap text-zinc-600">{task.evidence}</p></div>
          <div><h4 className="font-medium text-zinc-800">Why it matters</h4><p className="mt-1 whitespace-pre-wrap text-zinc-600">{task.why_it_matters}</p></div>
          <div><h4 className="font-medium text-zinc-800">Fix</h4><p className="mt-1 whitespace-pre-wrap text-zinc-600">{task.manual_fix}</p></div>
          <ul className="space-y-3">{task.subtasks.map(subtask => <li key={subtask.id}>
            <label className="flex items-start gap-3">
              <input type="checkbox" checked={!!subtask.completed_at} disabled={disabled}
                onChange={event => void onChange(task, event.target.checked, subtask.id)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-emerald-700" />
              <span className={subtask.completed_at ? 'text-zinc-500 line-through' : 'text-zinc-700'}>{subtask.title}</span>
            </label>
          </li>)}</ul>
          <details className="text-zinc-600">
            <summary className="cursor-pointer text-xs font-medium text-zinc-700">Coding-agent instruction</summary>
            <p className="mt-2 whitespace-pre-wrap border-l-2 border-emerald-200 pl-3">{task.agent_prompt}</p>
          </details>
          {task.completed_at && <p className="text-xs text-zinc-500">Marked complete {new Date(task.completed_at).toLocaleDateString()}</p>}
        </div>}
      </div>
    );
  }

  const stages = [...new Set(pending.map(task => task.stage))];
  return (
    <section aria-label="SEO tasks" className="min-w-0">
      <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
        <h2 className="text-base font-semibold text-zinc-900">Tasks</h2>
        <span className="text-xs text-zinc-500">{pending.length} open</span>
      </div>
      {pending.length === 0 && <p className="py-6 text-sm text-zinc-500">{completed.length ? 'All tasks completed.' : 'No open tasks.'}</p>}
      {stages.map(stage => <section key={stage} className="mt-5">
        <h3 className="text-xs font-semibold text-emerald-800">{STAGE_LABELS[stage] ?? stage}</h3>
        {pending.filter(task => task.stage === stage).map(task => taskRow(task))}
      </section>)}
      {completed.length > 0 && <section className="mt-8">
        <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-500"><CheckCheck className="h-4 w-4 text-emerald-700" />Completed ({completed.length})</h3>
        {completed.map(task => taskRow(task, true))}
      </section>}
    </section>
  );
}
