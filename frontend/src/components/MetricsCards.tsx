import { MetricsResponse } from '@/lib/api';
import { formatDuration, formatTokens } from '@/lib/utils';

interface CardProps {
  label: string;
  value: string;
  sub?: string;
  tone?: 'good' | 'bad';
}

function MetricCard({ label, value, sub, tone }: CardProps) {
  const valueColor =
    tone === 'good' ? 'text-good' : tone === 'bad' ? 'text-bad' : 'text-ink';
  return (
    <div className="border border-line p-5">
      <p className="text-xs uppercase tracking-wide text-muted mb-3">{label}</p>
      <p className={`text-3xl font-bold leading-none tabular-nums ${valueColor}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-muted mt-2">{sub}</p>}
    </div>
  );
}

interface Props {
  metrics: MetricsResponse;
}

export function MetricsCards({ metrics }: Props) {
  const rate = metrics.success_rate_pct ?? 0;
  const hasRuns = metrics.runs_total > 0;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <MetricCard
        label="Success rate"
        value={`${rate.toFixed(1)}%`}
        sub={`${metrics.runs_successful} of ${metrics.runs_total} runs`}
        tone={hasRuns ? (rate >= 50 ? 'good' : 'bad') : undefined}
      />
      <MetricCard
        label="Avg duration"
        value={formatDuration(metrics.avg_duration_ms)}
        sub={
          metrics.p95_duration_ms != null
            ? `p95 ${formatDuration(metrics.p95_duration_ms)}`
            : undefined
        }
      />
      <MetricCard
        label="Avg tokens"
        value={formatTokens(metrics.avg_tokens_per_run)}
        sub="per task"
      />
      <MetricCard
        label="Avg revisions"
        value={(metrics.avg_revisions ?? 0).toFixed(1)}
        sub="critic cycles"
      />
    </div>
  );
}
