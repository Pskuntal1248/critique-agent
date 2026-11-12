'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { fetchAuthConfig, type AuthConfig } from '@/lib/api';

/** Storage claims follow what the backend reports, never an assumption. */
export function DemoBanner() {
  const [cfg, setCfg] = useState<AuthConfig | null>(null);
  useEffect(() => { fetchAuthConfig().then(setCfg); }, []);
  const durable = cfg?.durable === true;
  return (
    <aside className="max-w-6xl mx-auto px-6 pt-4 text-sm text-muted">
      Public BYOK demo. <Link href="/settings" className="underline font-medium">Settings: choose your provider, model and API key</Link>.
      {' '}Your provider may charge for calls.
      {' '}{durable
        ? cfg?.google
          ? 'Runs are stored in the server database. Sign in to keep access to them.'
          : 'Runs are stored in the server database, but without an account only this browser tab can open them.'
        : 'Session data resets when the server restarts.'}
      {' '}Adapted from AgentForge.
    </aside>
  );
}
