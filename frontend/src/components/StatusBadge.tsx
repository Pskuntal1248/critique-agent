import { cn } from '@/lib/utils';

// Good = solid green, bad = solid red, in progress = solid black, rest = neutral.
const GOOD = 'bg-good text-white';
const BAD = 'bg-bad text-white';
const ACTIVE = 'bg-ink text-white';
const NEUTRAL = 'bg-white text-muted border border-line';

const STATUS_STYLES: Record<string, string> = {
  pending: NEUTRAL,
  running: ACTIVE,
  planning: ACTIVE,
  researching: ACTIVE,
  analysing: ACTIVE,
  analyzing: ACTIVE,
  critiquing: ACTIVE,
  writing: ACTIVE,
  awaiting_approval: 'bg-white text-ink border border-dashed border-ink',
  complete: GOOD,
  completed: GOOD,
  best_effort: 'bg-white text-ink border border-ink',
  failed: BAD,
  cancelled: NEUTRAL,
};

interface Props {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: Props) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 text-xs font-medium uppercase tracking-wide',
        STATUS_STYLES[status] ?? NEUTRAL,
        className,
      )}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}
