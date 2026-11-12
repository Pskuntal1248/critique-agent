'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { setAuthToken } from '@/lib/api';

export default function AuthCallbackPage() {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    const token = params.get('token');
    // Remove the token from the address bar and history straight away.
    window.history.replaceState(null, '', '/auth/callback');
    if (token && token.startsWith('ca1.')) {
      setAuthToken(token);
      window.location.replace('/');
    } else {
      setFailed(true);
    }
  }, []);
  if (!failed) return <p className="p-8 text-sm text-muted">Signing you in...</p>;
  return (
    <main className="max-w-xl mx-auto p-8">
      <h1 className="text-xl font-bold mb-2">Sign-in did not finish</h1>
      <p className="text-sm text-muted mb-4">
        You can try again, or keep using Critique without an account. Runs started without signing in are
        kept for this browser session only.
      </p>
      <Link href="/" className="underline">Back to dashboard</Link>
    </main>
  );
}
