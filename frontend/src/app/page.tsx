'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  api,
  HealthResponse,
  MetricsResponse,
  TaskSummary,
} from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';
import {
  formatDuration,
  formatTokens,
  relativeTime,
  shortId,
} from '@/lib/utils';

const STEPS = ['Plan', 'Research', 'Analyse', 'Critique', 'Write'];

const EXAMPLES = [
  {
    theme: 'Fintech',
    title: 'UPI-led fintech: top 3 opportunities',
    task: "Research India's UPI-led fintech market and identify the top 3 investment opportunities for 2025-26. Cover market size, key players such as PhonePe, Paytm and Google Pay, and the RBI/NPCI regulatory environment.",
  },
  {
    theme: 'Mobility',
    title: 'Electric two-wheelers in India',
    task: 'Analyse the Indian electric two-wheeler market. Compare Ola Electric, Ather Energy, TVS and Bajaj on market share, pricing and charging infrastructure, and explain how the FAME-II and PM E-DRIVE subsidies affect growth.',
  },
  {
    theme: 'Commerce',
    title: 'Blinkit vs Zepto vs Instamart',
    task: 'Compare Blinkit, Zepto and Swiggy Instamart. Cover dark store economics, unit economics, funding rounds and the 3 biggest risks for investors in tier-1 Indian cities.',
  },
];

function Stat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: 'good' | 'bad';
}) {
  const color =
    tone === 'good' ? 'text-good' : tone === 'bad' ? 'text-bad' : 'text-ink';
  return (
    <div className="bg-white px-6 py-5">
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className={`mt-2 text-3xl font-bold leading-none tabular-nums ${color}`}>
        {value}
      </dd>
      {sub && <p className="mt-2 text-xs text-muted">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [taskIdInput, setTaskIdInput] = useState('');

  useEffect(() => {
    Promise.all([api.health(), api.metrics(), api.listTasks(8)])
      .then(([h, m, t]) => {
        setHealth(h);
        setMetrics(m);
        setTasks(t);
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Failed to connect to backend'),
      )
      .finally(() => setLoading(false));
  }, []);

  const lookup = () => {
    const id = taskIdInput.trim();
    if (id) router.push(`/tasks/${id}`);
  };

  const online = health?.status === 'ok';
  const hasRuns = (metrics?.runs_total ?? 0) > 0;
  const rate = metrics?.success_rate_pct ?? 0;
  const dash = '—';

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="text-ink">
        <div className="pt-4 pb-10 flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <h1 className="text-5xl font-bold tracking-tight leading-[1.05]">
              Research that
              <br />
              argues with itself.
            </h1>
            <p className="mt-4 text-base leading-relaxed text-muted">
              Describe a question. Critique plans it, researches the web,
              analyses what it finds, and a critic challenges the analysis
              before the report is written.
            </p>
          </div>
          <div className="flex flex-col items-start gap-3">
            <Link
              href="/tasks/new"
              className="bg-accent hover:bg-accent-hover text-ink text-sm font-medium px-6 py-3 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
            >
              Start a research task
            </Link>
            <span
              className={`flex items-center gap-2 text-xs font-medium ${
                loading ? 'text-ink' : online ? 'text-ink' : 'text-bad'
              }`}
            >
              <span
                aria-hidden
                className={`h-2 w-2 rounded-full ${
                  loading ? 'bg-line' : online ? 'bg-good' : 'bg-bad'
                }`}
              />
              {loading
                ? 'Connecting…'
                : online
                  ? `API online${health?.provider ? `, ${health.provider}` : ''}`
                  : 'API offline'}
            </span>
          </div>
        </div>

        <ol className="grid grid-cols-5 border border-line">
          {STEPS.map((step, i) => (
            <li
              key={step}
              className="px-4 py-3 text-xs font-medium border-l border-line first:border-l-0"
            >
              <span className="tabular-nums mr-2 opacity-60">0{i + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      </section>

      {error && (
        <div role="alert" className="border-l-4 border-bad px-4 py-3 text-sm">
          <p className="font-bold text-bad">Backend unreachable</p>
          <p className="text-ink mt-0.5">{error}</p>
          <p className="text-xs text-muted mt-1">
            Check that the API is running and that{' '}
            <code className="font-mono">NEXT_PUBLIC_API_BASE_URL</code> is
            correct.
          </p>
        </div>
      )}

      {/* Stats */}
      <section aria-label="Last 24 hours">
        <h2 className="text-sm font-bold uppercase tracking-wide text-ink mb-4">
          Last 24 hours
        </h2>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-px bg-line border border-line">
          <Stat
            label="Success rate"
            value={hasRuns ? `${rate.toFixed(0)}%` : dash}
            sub={
              hasRuns
                ? `${metrics?.runs_successful} of ${metrics?.runs_total} runs`
                : 'No runs yet'
            }
            tone={hasRuns ? (rate >= 50 ? 'good' : 'bad') : undefined}
          />
          <Stat
            label="Avg duration"
            value={hasRuns ? formatDuration(metrics?.avg_duration_ms) : dash}
            sub={
              hasRuns && metrics?.p95_duration_ms != null
                ? `p95 ${formatDuration(metrics.p95_duration_ms)}`
                : undefined
            }
          />
          <Stat
            label="Avg tokens"
            value={hasRuns ? formatTokens(metrics?.avg_tokens_per_run) : dash}
            sub={hasRuns ? 'per task' : undefined}
          />
          <Stat
            label="Avg revisions"
            value={hasRuns ? (metrics?.avg_revisions ?? 0).toFixed(1) : dash}
            sub={hasRuns ? 'critic cycles per task' : undefined}
          />
        </dl>
      </section>

      {/* Recent tasks */}
      <section aria-label="Recent tasks">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-4">
          <h2 className="text-sm font-bold uppercase tracking-wide text-ink">
            Recent tasks
          </h2>
          <div className="flex gap-2">
            <label htmlFor="task-id" className="sr-only">
              Open a task by ID
            </label>
            <input
              id="task-id"
              type="text"
              value={taskIdInput}
              onChange={(e) => setTaskIdInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && lookup()}
              placeholder="Open by task ID"
              className="w-64 border border-line px-3 py-1.5 text-sm placeholder-muted focus:outline-none focus:border-ink focus-visible:ring-2 focus-visible:ring-ink"
            />
            <button
              onClick={lookup}
              disabled={!taskIdInput.trim()}
              className="border border-ink text-ink hover:bg-ink hover:text-white disabled:opacity-30 disabled:hover:bg-white disabled:hover:text-ink text-sm font-medium px-4 py-1.5 transition-colors"
            >
              Open
            </button>
          </div>
        </div>

        {loading ? (
          <div className="border-t border-line">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-12 border-b border-line animate-pulse" />
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <div className="border border-line px-6 py-10">
            <p className="font-bold text-ink">No tasks yet</p>
            <p className="text-sm text-muted mt-1">
              Start from one of the examples below, or write your own.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-muted border-b border-ink">
                  <th className="py-2 pr-4 font-medium">Task</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium text-right">Critic</th>
                  <th className="py-2 pr-4 font-medium text-right">Tokens</th>
                  <th className="py-2 pr-4 font-medium text-right">Time</th>
                  <th className="py-2 font-medium text-right">Created</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr
                    key={t.task_id}
                    className="border-b border-line hover:bg-[#f6f6f6] transition-colors"
                  >
                    <td className="py-3 pr-4 max-w-md">
                      <Link
                        href={`/tasks/${t.task_id}`}
                        className="block text-ink font-medium truncate hover:underline decoration-ink decoration-2 underline-offset-4"
                      >
                        {t.original_task}
                      </Link>
                      <span className="text-xs text-muted font-mono">
                        {shortId(t.task_id)}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={t.status} />
                    </td>
                    <td
                      className={`py-3 pr-4 text-right tabular-nums font-medium ${
                        t.critic_score == null
                          ? 'text-muted'
                          : t.critic_score >= 0.75
                            ? 'text-good'
                            : 'text-bad'
                      }`}
                    >
                      {t.critic_score == null ? dash : t.critic_score.toFixed(2)}
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums text-ink">
                      {t.total_tokens > 0 ? formatTokens(t.total_tokens) : dash}
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums text-ink">
                      {formatDuration(t.total_duration_ms)}
                    </td>
                    <td className="py-3 text-right text-muted whitespace-nowrap">
                      {relativeTime(t.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Latency */}
      {metrics && Object.keys(metrics.agent_avg_latency_ms).length > 0 && (
        <section aria-label="Agent latency">
          <h2 className="text-sm font-bold uppercase tracking-wide text-ink mb-4">
            Average time per agent
          </h2>
          <div className="space-y-3 border-t border-line pt-4">
            {Object.entries(metrics.agent_avg_latency_ms)
              .sort(([, a], [, b]) => b - a)
              .map(([agent, ms]) => {
                const maxMs = Math.max(
                  ...Object.values(metrics.agent_avg_latency_ms),
                );
                const pct = maxMs > 0 ? (ms / maxMs) * 100 : 0;
                return (
                  <div key={agent} className="flex items-center gap-4">
                    <span className="w-24 text-sm text-ink capitalize">
                      {agent}
                    </span>
                    <div className="flex-1 bg-line h-2">
                      <div
                        className="bg-ink h-2 transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-16 text-right text-sm text-muted tabular-nums">
                      {formatDuration(ms)}
                    </span>
                  </div>
                );
              })}
          </div>
        </section>
      )}

      {/* Examples */}
      <section aria-label="Examples">
        <h2 className="text-sm font-bold uppercase tracking-wide text-ink mb-4">
          Start from an example
        </h2>
        <ul className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {EXAMPLES.map((ex) => (
            <li key={ex.title}>
              <Link
                href={`/tasks/new?q=${encodeURIComponent(ex.task)}`}
                className="group block h-full border border-line p-5 hover:border-ink hover:bg-[#f6f6f6] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ink"
              >
                <span className="text-xs uppercase tracking-wide text-muted">
                  {ex.theme}
                </span>
                <span className="block mt-2 text-base font-bold text-ink">
                  {ex.title}
                </span>
                <span className="block mt-3 text-sm text-muted line-clamp-3">
                  {ex.task}
                </span>
                <span className="block mt-4 text-sm font-medium text-ink underline decoration-ink decoration-2 underline-offset-4">
                  Use this task
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
