'use client';

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api, ApiError, ReviewResponse } from '@/lib/api';

export function ReviewDraft({ taskId }: { taskId: string }) {
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getReview(taskId)
      .then((r) => !cancelled && setReview(r))
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e.message : 'Could not load the draft.'));
    return () => {
      cancelled = true;
    };
  }, [taskId]);

  if (error) return <p className="text-sm text-bad">{error}</p>;
  if (!review) return <p className="text-sm text-muted">Loading the draft for review…</p>;

  return (
    <section className="space-y-6">
      <div className="border border-line">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-3">
          <h3 className="text-sm font-bold text-ink">Analysis draft</h3>
          <span className="text-xs text-muted">
            Not the final report. The report is written from this analysis after you approve.
          </span>
        </div>
        <div className="prose prose-sm max-w-none px-5 py-4">
          {review.analysis ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{review.analysis}</ReactMarkdown>
          ) : (
            <p className="text-muted">No draft was recorded for this run.</p>
          )}
        </div>
      </div>

      {review.critic_notes.length > 0 && (
        <div className="border border-line px-5 py-4">
          <h3 className="text-sm font-bold text-ink mb-2">Critic feedback</h3>
          <ul className="space-y-2 text-sm">
            {review.critic_notes.map((n) => (
              <li key={n.round}>
                <span className="text-muted">
                  Round {n.round}
                  {n.score !== null ? ` · score ${n.score.toFixed(2)}` : ''}
                  {n.approved === true ? ' · approved' : n.approved === false ? ' · revision requested' : ''}
                </span>
                {n.feedback && <p className="text-ink">{n.feedback}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {review.sources.length > 0 && (
        <div className="border border-line px-5 py-4">
          <h3 className="text-sm font-bold text-ink mb-2">Sources the researcher used</h3>
          <ol className="list-decimal pl-5 space-y-1 text-sm">
            {review.sources.map((s) => (
              <li key={s.url}>
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="underline">
                  {s.title}
                </a>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
