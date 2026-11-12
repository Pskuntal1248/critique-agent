import Link from 'next/link';
import type { Metadata } from 'next';
import './globals.css';
import { Navbar } from '@/components/Navbar';

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
        <Navbar />
        <aside className="max-w-6xl mx-auto px-6 pt-4 text-sm text-muted">
          Public BYOK demo. <Link href="/settings" className="underline font-medium">Settings: choose your provider, model and API key</Link>.
          {' '}Your provider may charge for calls. Session data resets when the server restarts.
          {' '}Adapted from AgentForge.
        </aside>
        <main className="max-w-6xl mx-auto px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
