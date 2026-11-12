import Link from 'next/link';
import type { Metadata } from 'next';
import './globals.css';
import { Navbar } from '@/components/Navbar';
import { DemoBanner } from '@/components/DemoBanner';

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
        <DemoBanner />
        <main className="max-w-6xl mx-auto px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
