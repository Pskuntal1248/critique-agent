import Link from 'next/link';
import type { Metadata } from 'next';
import './globals.css';
import { AppShell } from '@/components/AppShell';

export const metadata: Metadata = {
  title: 'Critique',
  description: 'Multi-agent research reports with a built-in critic',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-white text-ink min-h-screen antialiased font-sans">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
