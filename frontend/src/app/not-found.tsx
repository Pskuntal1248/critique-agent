import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="py-24">
      <p className="text-6xl font-bold text-ink mb-4">404</p>
      <h1 className="text-xl font-bold text-ink mb-2">Page not found</h1>
      <p className="text-sm text-muted mb-8">
        The page you are looking for does not exist.
      </p>
      <Link
        href="/"
        className="text-sm font-medium text-ink underline decoration-ink decoration-2 underline-offset-4"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
