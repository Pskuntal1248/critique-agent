'use client';

import { useState } from 'react';
import { AgentEventResponse, AgentStepResponse } from '@/lib/api';
import { StatusBadge } from './StatusBadge';
import { cn, formatDuration } from '@/lib/utils';

interface Props {
  events: AgentEventResponse[];
  steps: AgentStepResponse[];
}

type Tab = 'events' | 'steps';

export function AuditTabs({ events, steps }: Props) {
  const [tab, setTab] = useState<Tab>('steps');

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: 'steps', label: 'Steps', count: steps.length },
    { id: 'events', label: 'Events', count: events.length },
  ];

  return (
    <div>
      <div role="tablist" className="flex border-b border-line mb-4 gap-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              tab === t.id
                ? 'border-ink text-ink'
                : 'border-transparent text-muted hover:text-ink',
            )}
          >
            {t.label}
            <span className="ml-1.5 text-xs text-muted">{t.count}</span>
          </button>
        ))}
      </div>

      {tab === 'steps' && (
        <div className="overflow-x-auto">
          {steps.length === 0 ? (
            <p className="text-sm text-muted py-4">No steps recorded yet.</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-muted font-medium uppercase tracking-wide">
                  <th className="pb-2 pr-3 font-medium">#</th>
                  <th className="pb-2 pr-3 font-medium">Agent</th>
                  <th className="pb-2 pr-3 font-medium">Status</th>
                  <th className="pb-2 pr-3 text-right font-medium">Tokens</th>
                  <th className="pb-2 pr-3 text-right font-medium">Duration</th>
                  <th className="pb-2 font-medium">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {steps.map((step) => (
                  <tr key={step.id}>
                    <td className="py-2 pr-3 text-muted tabular-nums">
                      {step.step_number}
                    </td>
                    <td className="py-2 pr-3 font-medium text-ink capitalize">
                      {step.agent_name}
                    </td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={step.status} />
                    </td>
                    <td className="py-2 pr-3 text-right text-ink tabular-nums">
                      {step.tokens_used.toLocaleString()}
                    </td>
                    <td className="py-2 pr-3 text-right text-ink tabular-nums">
                      {formatDuration(step.duration_ms)}
                    </td>
                    <td className="py-2 text-bad max-w-[120px] truncate">
                      {step.error ?? ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'events' && (
        <div className="max-h-64 overflow-y-auto">
          {events.length === 0 ? (
            <p className="text-sm text-muted py-4">No events recorded yet.</p>
          ) : (
            <ul className="divide-y divide-line">
              {events.map((ev) => (
                <li key={ev.id} className="flex items-center gap-3 py-1.5 text-xs">
                  <span className="font-mono text-muted w-6 text-right flex-shrink-0">
                    {ev.id}
                  </span>
                  <span className="font-medium text-ink w-36 truncate">
                    {ev.event_type}
                  </span>
                  <span className="text-muted w-20 truncate capitalize">
                    {ev.agent_name ?? ''}
                  </span>
                  <span className="ml-auto text-muted flex-shrink-0 tabular-nums">
                    {new Date(ev.created_at).toLocaleTimeString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
