'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchAuthConfig, type AuthConfig } from '@/lib/api';

/** Storage claims follow what the backend reports, never an assumption. */
export function storageNote(cfg: AuthConfig | null): string {
  if (cfg === null || cfg.unreachable) return ''; // unknown until /auth/config answers, so say nothing about storage
  if (cfg?.external_database) {
    return cfg.google
      ? 'An external database is configured. Sign in to keep access to your runs.'
      : 'An external database is configured, but without an account only this browser tab can open your runs.';
  }
  return 'Session data resets when the server restarts.';
}

export function LandingNote() {
  const [cfg, setCfg] = useState<AuthConfig | null>(null);
  useEffect(() => { fetchAuthConfig().then(setCfg); }, []);
  return (
    <div className="small">
      Bring your own model key. Your provider may charge for calls. {storageNote(cfg)} No account needed to try it.
    </div>
  );
}

export const DEMO_NOTICE_EVENT = 'critique:show-demo-notice';
const SEEN_KEY = 'critique.demoNoticeSeen';

/** The "Public BYOK demo" notice as a dismissible popup: shown once per tab, reopenable from the sidebar. */
export function DemoBanner() {
  const pathname = usePathname();
  const [cfg, setCfg] = useState<AuthConfig | null>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => { fetchAuthConfig().then(setCfg); }, []);
  useEffect(() => {
    try { if (!sessionStorage.getItem(SEEN_KEY)) setOpen(true); } catch { /* ignore */ }
    const show = () => setOpen(true);
    window.addEventListener(DEMO_NOTICE_EVENT, show);
    return () => window.removeEventListener(DEMO_NOTICE_EVENT, show);
  }, []);
  const dialogRef = useRef<HTMLDivElement>(null);
  const portalRef = useRef<HTMLDivElement | null>(null);
  const close = () => {
    setOpen(false);
    try { sessionStorage.setItem(SEEN_KEY, '1'); } catch { /* ignore */ }
  };
  // Focus trap, Escape, background inert, and focus restoration while the dialog is open.
  useEffect(() => {
    if (!open || pathname === '/') return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = dialogRef.current;
    const inerted: HTMLElement[] = [];
    Array.from(document.body.children).forEach((el) => {
      const h = el as HTMLElement;
      if (h === portalRef.current || h.tagName === 'SCRIPT' || h.hasAttribute('inert')) return;
      h.setAttribute('inert', '');
      inerted.push(h);
    });
    const focusables = () =>
      Array.from(dialog?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])') ?? []);
    focusables()[0]?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { close(); return; }
      if (e.key !== 'Tab') return;
      const f = focusables();
      if (f.length === 0) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      inerted.forEach((h) => h.removeAttribute('inert'));
      previous?.focus?.();
    };
  }, [open, pathname]);
  if (pathname === '/' || !open) return null; // the landing page carries its own short note
  const external = cfg?.external_database === true;
  return createPortal(
    <div ref={portalRef} className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4" onClick={close}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="demo-notice-title"
        className="w-full max-w-md bg-white border border-ink p-6 text-sm text-muted"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="demo-notice-title" className="text-lg font-bold text-ink">Public BYOK demo</h2>
        <p className="mt-3">
          Bring your own model key. <Link href="/settings" onClick={close} className="underline font-medium text-ink">Choose your provider, model and API key in Settings</Link>.
          {' '}Your provider may charge for calls.
        </p>
        <p className="mt-2">
          {external
            ? cfg?.google
              ? 'An external database is configured. Sign in to keep access to your runs.'
              : 'An external database is configured, but without an account only this browser tab can open your runs.'
            : storageNote(cfg)}
        </p>
        <p className="mt-2">Adapted from AgentForge.</p>
        <button type="button" onClick={close} className="mt-5 bg-accent hover:bg-accent-hover text-ink font-medium px-5 py-2">
          Got it
        </button>
      </div>
    </div>,
    document.body,
  );
}
