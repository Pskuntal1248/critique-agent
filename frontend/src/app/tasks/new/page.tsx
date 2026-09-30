'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, ApiError } from '@/lib/api';

const MIN_LENGTH = 10;
const MAX_LENGTH = 4000;

export default function NewTaskPage() {
  const router = useRouter();
  const [task, setTask] = useState('');
  const [humanInLoop, setHumanInLoop] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Prefill from ?q= (used by the dashboard examples).
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    if (q) setTask(q.slice(0, MAX_LENGTH));
  }, []);

  const charCount = task.length;
  const isValid = charCount >= MIN_LENGTH && charCount <= MAX_LENGTH;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!isValid || loading) return;

    setLoading(true);
    setError(null);

    try {
      const run = await api.createTask({ task, human_in_loop: humanInLoop });
      router.push(`/tasks/${run.task_id}`);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? `Error ${e.status}: ${e.message}`
          : 'Failed to create task. Is the backend running?',
      );
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <Link
        href="/"
        className="text-sm text-muted hover:text-ink transition-colors"
      >
        Back to dashboard
      </Link>

      <div className="mt-6 mb-8">
        <h1 className="text-4xl font-bold tracking-tight text-ink">
          New research task
        </h1>
        <p className="text-sm text-muted mt-2">
          Planner, researcher, analyst, critic, writer. The critic reviews the
          analysis before the report is written.
        </p>
      </div>

      <form onSubmit={(e) => void handleSubmit(e)} className="space-y-6">
        <div>
          <label
            htmlFor="task"
            className="block text-sm font-bold text-ink mb-2"
          >
            Task description
          </label>
          <textarea
            id="task"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="e.g. Research India's UPI-led fintech market and identify the top 3 investment opportunities for 2025-26, including market size, key players such as PhonePe, Paytm and Google Pay, and the RBI/NPCI regulatory environment."
            rows={7}
            disabled={loading}
            className="w-full border border-line px-3 py-2.5 text-sm placeholder-muted focus:outline-none focus:border-ink focus-visible:ring-2 focus-visible:ring-ink resize-none disabled:opacity-60"
          />
          <div className="flex items-center justify-between mt-2 text-xs">
            <span
              className={`tabular-nums ${
                charCount > MAX_LENGTH ? 'text-bad font-medium' : 'text-muted'
              }`}
            >
              {charCount.toLocaleString()} / {MAX_LENGTH.toLocaleString()}
            </span>
            {charCount > 0 && charCount < MIN_LENGTH && (
              <span className="text-bad">Minimum {MIN_LENGTH} characters</span>
            )}
            {charCount > MAX_LENGTH && (
              <span className="text-bad font-medium">
                {charCount - MAX_LENGTH} characters over the limit
              </span>
            )}
          </div>
        </div>

        <label className="flex items-start gap-3 cursor-pointer border border-line p-4">
          <input
            type="checkbox"
            checked={humanInLoop}
            onChange={(e) => setHumanInLoop(e.target.checked)}
            disabled={loading}
            className="mt-0.5 h-4 w-4 accent-[#111111] disabled:opacity-60"
          />
          <span>
            <span className="block text-sm font-bold text-ink">
              Review before writing
            </span>
            <span className="block text-xs text-muted mt-1 leading-relaxed">
              The pipeline pauses after the critic approves and waits for you.
              You can approve, reject, or send feedback for another analysis.
            </span>
          </span>
        </label>

        {error && (
          <div role="alert" className="border-l-4 border-bad px-4 py-3 text-sm text-bad">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={!isValid || loading}
            className="bg-accent hover:bg-accent-hover text-ink text-sm font-medium px-6 py-2.5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Submitting…' : 'Start research'}
          </button>
          <Link
            href="/"
            className="px-6 py-2.5 text-sm font-medium text-ink border border-line hover:border-ink transition-colors"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
