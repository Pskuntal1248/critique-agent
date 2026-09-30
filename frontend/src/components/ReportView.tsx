'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
}

export function ReportView({ content }: Props) {
  return (
    <div className="prose prose-sm max-w-none prose-headings:font-bold prose-headings:text-ink prose-p:text-ink prose-li:text-ink prose-a:text-ink prose-a:underline prose-a:decoration-ink prose-a:decoration-2 prose-a:underline-offset-2 prose-code:bg-[#f6f6f6] prose-code:px-1 prose-code:py-0.5 prose-code:text-ink prose-code:before:content-none prose-code:after:content-none prose-pre:bg-ink prose-pre:text-white prose-th:text-ink prose-table:text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
