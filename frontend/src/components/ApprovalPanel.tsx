'use client';

import { useState } from 'react';
import { api, ApiError } from '@/lib/api';

interface Props {
  taskId: string;
  onDecision: () => void;
}

export function ApprovalPanel({ taskId, onDecision }: Props) {
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (decision: 'approve' | 'reject' | 'feedback') => {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      await api.approveTask(taskId, {
        decision,
        feedback: decision === 'feedback' ? feedback : undefined,
      });
      onDecision();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="border border-ink bg-[#f6f6f6] p-5">
      <h3 className="text-sm font-bold text-ink mb-1">Review required</h3>
      <p className="text-sm text-muted mb-4">
        The pipeline is paused. Approve to write the report, send feedback to
        trigger another analysis, or reject to stop.
      </p>

      <label htmlFor="feedback" className="sr-only">
        Feedback for the analyst
      </label>
      <textarea
        id="feedback"
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Feedback for the analyst (required to send feedback)"
        rows={3}
        disabled={loading}
        className="w-full border border-line bg-white px-3 py-2 text-sm placeholder-muted focus:outline-none focus:border-ink focus-visible:ring-2 focus-visible:ring-ink resize-none disabled:opacity-60 mb-3"
      />

      {error && <p className="text-sm text-bad font-medium mb-3">{error}</p>}

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => void submit('approve')}
          disabled={loading}
          className="bg-good hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium px-5 py-2 transition-opacity"
        >
          Approve
        </button>
        <button
          onClick={() => void submit('feedback')}
          disabled={loading || !feedback.trim()}
          className="bg-accent hover:bg-accent-hover disabled:opacity-50 text-ink text-sm font-medium px-5 py-2 transition-colors"
        >
          Send feedback
        </button>
        <button
          onClick={() => void submit('reject')}
          disabled={loading}
          className="bg-bad hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium px-5 py-2 transition-opacity"
        >
          Reject
        </button>
      </div>
    </section>
  );
}
