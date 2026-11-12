'use client';

import React from 'react';
import { Renderer } from '@openuidev/react-lang';
import { reportLibrary } from './library';
import { reportToOpenUi } from '@/lib/reportToUi';
import { ReportView } from '@/components/ReportView';
import './report-ui.css';

class Boundary extends React.Component<{ fallback: React.ReactNode; children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

/**
 * Content-adaptive report view. Falls back to the plain Markdown view when the
 * report has no usable structure, when the renderer reports errors, or if rendering throws.
 */
export function ReportUI({ content }: { content: string }) {
  const [plain, setPlain] = React.useState(false);
  const [errors, setErrors] = React.useState(0);
  const program = React.useMemo(() => {
    try { return reportToOpenUi(content); } catch { return null; }
  }, [content]);
  const md = <ReportView content={content} />;
  if (!program || plain || errors > 0) {
    return (
      <div>
        {program && (
          <button type="button" className="mb-3 border border-line px-3 py-1 text-xs" onClick={() => { setErrors(0); setPlain(false); }}>
            {errors > 0 ? 'Structured view unavailable. Showing plain report.' : 'Show structured view'}
          </button>
        )}
        {md}
      </div>
    );
  }
  return (
    <div>
      <button type="button" className="mb-3 border border-line px-3 py-1 text-xs" onClick={() => setPlain(true)}>Plain view</button>
      <Boundary fallback={md}>
        <div className="ru">
          <Renderer library={reportLibrary} response={program} isStreaming={false} onError={(e) => setErrors(e.length)} />
        </div>
      </Boundary>
    </div>
  );
}
