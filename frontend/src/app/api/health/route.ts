/**
 * GET /api/health
 *
 * Lightweight health-check endpoint for Railway and other platforms that need
 * to verify the Next.js server is running.
 */
export function GET() {
  return Response.json({ status: 'ok' });
}
