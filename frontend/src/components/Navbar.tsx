'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchAuthConfig, fetchMe, GOOGLE_LOGIN_URL, setAuthToken, type AuthUser } from '@/lib/api';

const API_DOCS_URL = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/docs`;

export function Navbar() {
  const [googleOn, setGoogleOn] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  useEffect(() => {
    fetchAuthConfig().then((c) => setGoogleOn(c.google));
    fetchMe().then(setUser);
  }, []);
  return (
    <header className="border-b border-line bg-white sticky top-0 z-10">
      <nav
        aria-label="Main"
        className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between"
      >
        <Link
          href="/"
          className="text-lg font-bold tracking-tight text-ink"
        >
          Critique
        </Link>

        <div className="flex items-center gap-6 text-sm">
          <Link href="/" className="text-muted hover:text-ink transition-colors">
            Dashboard
          </Link>
          <a
            href={API_DOCS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted hover:text-ink transition-colors"
          >
            API docs
          </a>
          {user ? (
            <span className="flex items-center gap-3 text-muted">
              <span className="hidden sm:inline max-w-[160px] truncate" title={user.email}>{user.email}</span>
              <button
                type="button"
                className="hover:text-ink underline"
                onClick={() => { setAuthToken(null); window.location.href = '/'; }}
              >
                Sign out
              </button>
            </span>
          ) : googleOn ? (
            <a href={GOOGLE_LOGIN_URL} className="text-muted hover:text-ink transition-colors">
              Sign in with Google
            </a>
          ) : null}
          <Link
            href="/tasks/new"
            className="bg-accent hover:bg-accent-hover text-ink font-medium px-4 py-1.5 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
          >
            New task
          </Link>
        </div>
      </nav>
    </header>
  );
}
