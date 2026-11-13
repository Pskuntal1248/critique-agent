'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { api, fetchAuthConfig, fetchMe, GOOGLE_LOGIN_URL, signOut, type AuthUser, type TaskSummary } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import { DemoBanner, DEMO_NOTICE_EVENT } from '@/components/DemoBanner';
import { cn } from '@/lib/utils';

const API_DOCS_URL = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/docs`;

function Icon({ d }: { d: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="shrink-0">
      <path d={d} />
    </svg>
  );
}
const ICONS = {
  plus: 'M12 5v14M5 12h14',
  home: 'M3 11l9-8 9 8M5 10v10h14V10',
  gear: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z',
  book: 'M4 19.5A2.5 2.5 0 016.5 17H20V3H6.5A2.5 2.5 0 004 5.5v14zM20 17v4H6.5A2.5 2.5 0 014 18.5',
  menu: 'M3 6h18M3 12h18M3 18h18',
  close: 'M6 6l12 12M18 6L6 18',
  panel: 'M3 4h18v16H3zM9 4v16',
  info: 'M12 22a10 10 0 100-20 10 10 0 000 20zM12 16v-4M12 8h.01',
};

function dotClass(status: string) {
  if (status === 'complete' || status === 'completed') return 'bg-good';
  if (status === 'failed') return 'bg-bad';
  if (status === 'awaiting_approval') return 'bg-white border border-dashed border-ink';
  if (status === 'cancelled' || status === 'pending' || status === 'best_effort') return 'bg-line';
  return 'bg-ink';
}

function Sidebar({ collapsed, onToggle, onNavigate }: { collapsed: boolean; onToggle?: () => void; onNavigate?: () => void }) {
  const pathname = usePathname();
  const [googleOn, setGoogleOn] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [runs, setRuns] = useState<TaskSummary[] | null>(null);
  useEffect(() => {
    fetchAuthConfig().then((c) => setGoogleOn(c.google));
    fetchMe().then(setUser);
  }, []);
  useEffect(() => {
    let live = true;
    api.listTasks(12).then((r) => live && setRuns(r)).catch(() => live && setRuns([]));
    return () => { live = false; };
  }, [pathname]);

  const item = (href: string, label: string, icon: string, external = false) => {
    const active = !external && (href === '/dashboard' ? pathname === '/dashboard' : pathname === href);
    const cls = cn(
      'flex items-center gap-3 px-3 py-2 text-sm transition-colors',
      active ? 'bg-ink text-white' : 'text-muted hover:text-ink hover:bg-[#f3f3f3]',
      collapsed && 'justify-center px-0',
    );
    const inner = (<><Icon d={icon} />{!collapsed && <span>{label}</span>}</>);
    return external
      ? <a href={href} target="_blank" rel="noopener noreferrer" className={cls} title={label} aria-label={label}>{inner}</a>
      : <Link href={href} onClick={onNavigate} className={cls} title={label} aria-label={label} aria-current={active ? 'page' : undefined}>{inner}</Link>;
  };

  return (
    <div className="flex flex-col h-full">
      <div className={cn('h-14 flex items-center border-b border-line px-4', collapsed && 'justify-center px-0')}>
        <Link href="/" className="text-lg font-bold tracking-tight text-ink" aria-label="Critique home">
          {collapsed ? 'C' : 'Critique'}
        </Link>
      </div>
      <div className="p-3 space-y-1">
        <Link
          href="/tasks/new"
          onClick={onNavigate}
          title="New task"
          aria-label="New task"
          className={cn('flex items-center gap-3 bg-accent hover:bg-accent-hover text-ink font-medium px-3 py-2 text-sm transition-colors', collapsed && 'justify-center px-0')}
        >
          <Icon d={ICONS.plus} />{!collapsed && <span>New task</span>}
        </Link>
        {item('/dashboard', 'Dashboard', ICONS.home)}
        {item('/settings', 'Settings', ICONS.gear)}
      </div>
      {!collapsed && (
        <div className="px-3 pt-3 flex-1 min-h-0 overflow-y-auto border-t border-line">
          <h2 className="px-3 pb-2 text-xs uppercase tracking-wide text-muted">Runs</h2>
          {runs === null ? (
            <p className="px-3 text-sm text-muted">Loading…</p>
          ) : runs.length === 0 ? (
            <p className="px-3 text-sm text-muted">No runs yet.</p>
          ) : (
            <ul className="space-y-0.5">
              {runs.map((r) => {
                const href = `/tasks/${r.task_id}`;
                const active = pathname === href;
                return (
                  <li key={r.task_id}>
                    <Link
                      href={href}
                      onClick={onNavigate}
                      title={`${r.original_task} (${r.status.replace(/_/g, ' ')})`}
                      className={cn('flex items-start gap-2 px-3 py-2 text-sm leading-snug', active ? 'bg-[#f3f3f3] text-ink font-medium' : 'text-muted hover:text-ink hover:bg-[#f3f3f3]')}
                    >
                      <span className={cn('mt-1.5 w-2 h-2 rounded-full shrink-0', dotClass(r.status))} aria-label={r.status.replace(/_/g, ' ')} />
                      <span className="line-clamp-2">{r.original_task}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
      {collapsed && <div className="flex-1" />}
      <div className="p-3 border-t border-line space-y-1">
        {item(API_DOCS_URL, 'API docs', ICONS.book, true)}
        <button
          type="button"
          onClick={() => { window.dispatchEvent(new Event(DEMO_NOTICE_EVENT)); onNavigate?.(); }}
          title="About this demo"
          aria-label="About this demo"
          className={cn('flex w-full items-center gap-3 px-3 py-2 text-sm text-muted hover:text-ink hover:bg-[#f3f3f3]', collapsed && 'justify-center px-0')}
        >
          <Icon d={ICONS.info} />{!collapsed && <span>About this demo</span>}
        </button>
        {user ? (
          !collapsed && (
            <div className="px-3 py-2 text-sm text-muted">
              <div className="truncate" title={user.email}>{user.email}</div>
              <button type="button" className="underline hover:text-ink" onClick={() => { signOut().then(() => { window.location.href = '/'; }); }}>Sign out</button>
            </div>
          )
        ) : googleOn && !collapsed ? (
          <a href={GOOGLE_LOGIN_URL} className="block px-3 py-2 text-sm text-muted hover:text-ink underline">Sign in with Google</a>
        ) : null}
        {onToggle && (
          <button
            type="button"
            onClick={onToggle}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={cn('flex w-full items-center gap-3 px-3 py-2 text-sm text-muted hover:text-ink hover:bg-[#f3f3f3]', collapsed && 'justify-center px-0')}
          >
            <Icon d={ICONS.panel} />{!collapsed && <span>Collapse</span>}
          </button>
        )}
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    try { setCollapsed(localStorage.getItem('critique.sidebar') === '1'); } catch { /* ignore */ }
  }, []);
  useEffect(() => { setOpen(false); }, [pathname]);
  const toggle = () => {
    setCollapsed((c) => {
      try { localStorage.setItem('critique.sidebar', c ? '0' : '1'); } catch { /* ignore */ }
      return !c;
    });
  };

  if (pathname === '/') {
    return (
      <>
        <Navbar />
        <main className="max-w-6xl mx-auto px-6 py-10">{children}</main>
      </>
    );
  }

  return (
    <div className="min-h-screen md:flex md:gap-2 md:p-2 bg-[#f1f1f1]">
      <DemoBanner />
      <aside
        aria-label="Main"
        className={cn('hidden md:block sticky top-2 h-[calc(100vh-1rem)] shrink-0 border border-line bg-white transition-[width]', collapsed ? 'w-16' : 'w-64')}
      >
        <Sidebar collapsed={collapsed} onToggle={toggle} />
      </aside>

      <div className="md:hidden sticky top-0 z-20 h-14 flex items-center justify-between px-4 border-b border-line bg-white">
        <button type="button" onClick={() => setOpen(true)} aria-label="Open menu" className="p-2 -ml-2"><Icon d={ICONS.menu} /></button>
        <Link href="/" className="text-lg font-bold tracking-tight text-ink">Critique</Link>
        <Link href="/tasks/new" className="bg-accent text-ink font-medium px-3 py-1.5 text-sm">New task</Link>
      </div>
      {open && (
        <div className="md:hidden fixed inset-0 z-30 flex">
          <div className="w-72 max-w-[85%] bg-white h-full shadow-xl relative">
            <button type="button" onClick={() => setOpen(false)} aria-label="Close menu" className="absolute right-3 top-3 p-2 z-10"><Icon d={ICONS.close} /></button>
            <Sidebar collapsed={false} onNavigate={() => setOpen(false)} />
          </div>
          <button type="button" aria-label="Close menu" className="flex-1 bg-black/30" onClick={() => setOpen(false)} />
        </div>
      )}

      <div className="flex-1 min-w-0 md:border md:border-line bg-white">
        <main className="max-w-5xl mx-auto px-4 sm:px-8 py-6 sm:py-8">{children}</main>
      </div>
    </div>
  );
}
