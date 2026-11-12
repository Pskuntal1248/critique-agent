'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { fetchAuthConfig, type AuthConfig } from '@/lib/api';

/** Storage claims follow what the backend reports, never an assumption. */
export function DemoBanner() {
  const [cfg, setCfg] = useState<AuthConfig | null>(null);
  useEffect(() => { fetchAuthConfig().then(setCfg); }, []);
  const external = cfg?.external_database === true;
  return (
    <aside className="max-w-6xl mx-auto px-6 pt-4 text-sm text-muted">
      Public BYOK demo. <Link href="/settings" className="underline font-medium">Settings: choose your provider, model and API key</Link>.
      {' '}Your provider may charge for calls.
      {' '}{external
        ? cfg?.google
          ? 'An external database is configured. Sign in to keep access to your runs.'
          : 'An external database is configured, but without an account only this browser tab can open your runs.'
        : 'Session data resets when the server restarts.'}
      {' '}Adapted from AgentForge.
    </aside>
  );
}
