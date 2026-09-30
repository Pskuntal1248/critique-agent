'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  api,
  ApiError,
  AgentEventResponse,
  AgentStepResponse,
  StreamEvent,
  TaskResponse,
  streamTask,
} from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';
import { TaskTimeline } from '@/components/TaskTimeline';
import { ApprovalPanel } from '@/components/ApprovalPanel';
import { AuditTabs } from '@/components/AuditTabs';
import { ReportView } from '@/components/ReportView';
import {
  formatDuration,
  formatCost,
  formatTokens,
  relativeTime,
  shortId,
} from '@/lib/utils';

const TERMINAL_STATUSES = new Set([
  'complete',
  'failed',
  'cancelled',
  'best_effort',
]);

interface Props {
  taskId: string;
}

export function TaskDetailClient({ taskId }: Props) {
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<AgentEventResponse[]>([]);
  const [auditSteps, setAuditSteps] = useState<AgentStepResponse[]>([]);
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const cleanupStreamRef = useRef<(() => void) | null>(null);

  // ── Data fetching ────────────────────────────────────────────────────────

  const fetchAll = useCallback(async (): Promise<TaskResponse | null> => {
    try {
      const [t, evs, sts] = await Promise.all([
        api.getTask(taskId),
        api.getEvents(taskId).catch((): AgentEventResponse[] => []),
        api.getSteps(taskId).catch((): AgentStepResponse[] => []),
      ]);
      setTask(t);
      setAuditEvents(evs);
      setAuditSteps(sts);
      setFetchError(null);
      return t;
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.status === 404 ? 'Task not found' : `Error ${e.status}`}: ${e.message}`
          : 'Failed to load task';
      setFetchError(msg);
      return null;
    }
  }, [taskId]);

  // ── SSE streaming ────────────────────────────────────────────────────────

  const startStream = useCallback(
    (status: string) => {
      if (TERMINAL_STATUSES.has(status)) return;
      if (cleanupStreamRef.current) return; // already open

      setIsStreaming(true);
      const cleanup = streamTask(
        taskId,
        (ev: StreamEvent) => setStreamEvents((prev) => [...prev, ev]),
        () => {
          setIsStreaming(false);
          cleanupStreamRef.current = null;
          // Refresh audit data after stream ends
          void fetchAll();
        },
      );
      cleanupStreamRef.current = cleanup;
    },
    [taskId, fetchAll],
  );

  // ── Initial load ─────────────────────────────────────────────────────────

  useEffect(() => {
    setPageLoading(true);
    fetchAll()
      .then((t) => {
        if (t) startStream(t.status);
      })
      .finally(() => setPageLoading(false));

    return () => {
      cleanupStreamRef.current?.();
      cleanupStreamRef.current = null;
    };
  }, [fetchAll, startStream]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleRefresh = async () => {
    setRefreshing(true);
    const t = await fetchAll();
    if (t && !TERMINAL_STATUSES.has(t.status)) startStream(t.status);
    setRefreshing(false);
  };

  const handleCancel = async () => {
    setCancelLoading(true);
    setCancelError(null);
    try {
      await api.cancelTask(taskId);
      cleanupStreamRef.current?.();
      cleanupStreamRef.current = null;
      setIsStreaming(false);
      await fetchAll();
    } catch (e) {
      setCancelError(
        e instanceof ApiError ? e.message : 'Cancel failed',
      );
    } finally {
      setCancelLoading(false);
    }
  };

  const handleDownloadMd = async () => {
    setExportError(null);
    try {
      await api.downloadReportMd(taskId);
    } catch (e) {
      setExportError(
        e instanceof ApiError
          ? `Export failed (${e.status}): ${e.message}`
          : 'Could not download report. Try again.',
      );
    }
  };

  const handleDownloadJson = async () => {
    setExportError(null);
    try {
      await api.downloadReportJson(taskId);
    } catch (e) {
      setExportError(
        e instanceof ApiError
          ? `Export failed (${e.status}): ${e.message}`
          : 'Could not download report. Try again.',
      );
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  if (pageLoading) {
    return (
      <p className="py-20 text-sm text-muted" aria-live="polite">
        Loading…
      </p>
    );
  }

  if (fetchError || !task) {
    return (
      <div className="max-w-md py-20">
        <p className="text-bad font-bold mb-2" role="alert">
          {fetchError ?? 'Task not found'}
        </p>
        <Link
          href="/"
          className="text-sm font-medium text-ink underline decoration-ink decoration-2 underline-offset-4"
        >
          Back to dashboard
        </Link>
      </div>
    );
  }

  const isTerminal = TERMINAL_STATUSES.has(task.status);
  const canCancel = !isTerminal && !cancelLoading;
  const hasReport = Boolean(task.final_report);

  const metaItems = [
    { label: 'Model', value: task.model_name ?? '—' },
    { label: 'Provider', value: task.llm_provider ?? '—' },
    { label: 'Total tokens', value: formatTokens(task.total_tokens) },
    { label: 'Cost', value: formatCost(task.estimated_cost_usd) },
    { label: 'Prompt tokens', value: formatTokens(task.total_prompt_tokens) },
    {
      label: 'Completion tokens',
      value: formatTokens(task.total_completion_tokens),
    },
    {
      label: 'Critic score',
      value: task.critic_score != null ? task.critic_score.toFixed(2) : '—',
      tone:
        task.critic_score == null
          ? undefined
          : task.critic_score >= 0.75
            ? 'good'
            : 'bad',
    },
    { label: 'Revisions', value: String(task.revision_count) },
  ] as { label: string; value: string; tone?: 'good' | 'bad' }[];

  const secondaryBtn =
    'text-sm text-ink border border-line px-3 py-1.5 hover:border-ink disabled:opacity-50 transition-colors';

  return (
    <div className="space-y-8">
      <Link
        href="/"
        className="text-sm text-muted hover:text-ink transition-colors"
      >
        Back to dashboard
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold font-mono tracking-tight text-ink">
              {shortId(taskId)}
            </h1>
            <StatusBadge status={task.status} />
            {task.human_in_loop && (
              <span className="inline-flex items-center border border-ink text-ink px-2 py-0.5 text-xs font-medium uppercase tracking-wide">
                review on
              </span>
            )}
          </div>
          <p className="text-xs text-muted">
            Created {relativeTime(task.created_at)}
            {task.total_duration_ms != null &&
              ` · finished in ${formatDuration(task.total_duration_ms)}`}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {hasReport && (
            <>
              <button
                onClick={() => void handleDownloadMd()}
                title="Download Markdown report"
                className={secondaryBtn}
              >
                Download .md
              </button>
              <button
                onClick={() => void handleDownloadJson()}
                title="Download JSON report"
                className={secondaryBtn}
              >
                Download .json
              </button>
            </>
          )}
          <button
            onClick={() => void handleRefresh()}
            disabled={refreshing}
            className={secondaryBtn}
          >
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
          {canCancel && (
            <button
              onClick={() => void handleCancel()}
              className="text-sm text-bad border border-bad px-3 py-1.5 hover:bg-bad hover:text-white transition-colors"
            >
              Cancel task
            </button>
          )}
        </div>
      </div>

      {cancelError && (
        <div role="alert" className="border-l-4 border-bad px-4 py-2.5 text-sm text-bad">
          {cancelError}
        </div>
      )}

      {exportError && (
        <div
          role="alert"
          className="flex items-center justify-between border-l-4 border-bad px-4 py-2.5 text-sm text-ink"
        >
          <span>{exportError}</span>
          <button
            onClick={() => setExportError(null)}
            className="ml-4 text-muted hover:text-ink font-medium flex-shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}

      <section>
        <h2 className="text-xs font-bold uppercase tracking-wide text-muted mb-2">
          Task
        </h2>
        <p className="text-base text-ink leading-relaxed max-w-3xl">
          {task.original_task}
        </p>
      </section>

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-line border border-line">
        {metaItems.map(({ label, value, tone }) => (
          <div key={label} className="bg-white px-4 py-3">
            <dt className="text-xs text-muted mb-1">{label}</dt>
            <dd
              className={`text-sm font-bold truncate ${
                tone === 'good'
                  ? 'text-good'
                  : tone === 'bad'
                    ? 'text-bad'
                    : 'text-ink'
              }`}
            >
              {value}
            </dd>
          </div>
        ))}
      </dl>

      {task.status === 'awaiting_approval' && (
        <ApprovalPanel
          taskId={taskId}
          onDecision={() => void handleRefresh()}
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section>
          <h2 className="text-sm font-bold uppercase tracking-wide text-ink mb-4">
            Live events
          </h2>
          <TaskTimeline events={streamEvents} isStreaming={isStreaming} />
        </section>

        <section>
          <h2 className="text-sm font-bold uppercase tracking-wide text-ink mb-4">
            Execution audit
          </h2>
          <AuditTabs events={auditEvents} steps={auditSteps} />
        </section>
      </div>

      {hasReport && task.final_report && (
        <section className="border-t border-line pt-8">
          <h2 className="text-sm font-bold uppercase tracking-wide text-ink mb-6">
            Report
          </h2>
          <ReportView content={task.final_report} />
        </section>
      )}

      {task.error && (
        <section className="border-l-4 border-bad px-4 py-3">
          <h3 className="text-sm font-bold text-bad mb-1.5">Pipeline error</h3>
          <pre className="text-xs text-ink font-mono whitespace-pre-wrap break-all">
            {task.error}
          </pre>
        </section>
      )}
    </div>
  );
}
