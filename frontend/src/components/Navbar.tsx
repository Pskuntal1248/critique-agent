import Link from 'next/link';

const API_DOCS_URL = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/docs`;

export function Navbar() {
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
