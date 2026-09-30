import { StreamEvent } from '@/lib/api';
import { cn } from '@/lib/utils';

interface EventConfig {
  bar: string;
  label: string;
}

// The left bar carries the meaning: blue = in progress, green = good, red = bad.
const EVENT_CONFIG: Record<string, EventConfig> = {
  agent_start: { bar: 'border-ink', label: 'Started' },
  agent_complete: { bar: 'border-good', label: 'Completed' },
  awaiting_approval: { bar: 'border-ink', label: 'Awaiting approval' },
  task_complete: { bar: 'border-good', label: 'Task complete' },
  task_failed: { bar: 'border-bad', label: 'Task failed' },
  task_cancelled: { bar: 'border-line', label: 'Cancelled' },
};

interface Props {
  events: StreamEvent[];
  isStreaming: boolean;
}

export function TaskTimeline({ events, isStreaming }: Props) {
  if (events.length === 0 && !isStreaming) {
    return (
      <p className="text-sm text-muted py-6">
        No live events yet. Events appear as the pipeline runs.
      </p>
    );
  }

  return (
    <ol className="space-y-1 timeline-scroll max-h-72 overflow-y-auto pr-1">
      {events.map((ev, i) => {
        const cfg = EVENT_CONFIG[ev.type] ?? {
          bar: 'border-line',
          label: ev.type.replace(/_/g, ' '),
        };

        const agent = ev.data.agent as string | undefined;
        const tokens = ev.data.tokens as number | undefined;
        const step = ev.data.step as number | undefined;

        return (
          <li
            key={i}
            className={cn(
              'flex items-center gap-3 border-l-4 pl-3 py-1.5 text-xs',
              cfg.bar,
            )}
          >
            <span className="font-medium text-ink">{cfg.label}</span>
            {agent && <span className="text-muted capitalize">{agent}</span>}
            {step != null && <span className="text-muted">step {step}</span>}
            {tokens != null && (
              <span className="ml-auto text-muted tabular-nums">
                {tokens.toLocaleString()} tokens
              </span>
            )}
          </li>
        );
      })}

      {isStreaming && (
        <li className="text-xs text-muted pl-4 py-1.5" aria-live="polite">
          Streaming…
        </li>
      )}
    </ol>
  );
}
