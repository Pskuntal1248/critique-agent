/** @type {import('next').NextConfig} */
const nextConfig = {
  // react-markdown v9 and remark-gfm v4 are ESM-only.
  // Next.js 15 handles them in client bundles natively;
  // listing them here ensures the server-side bundler transpiles them too.
  transpilePackages: ['react-markdown', 'remark-gfm'],
};

export default nextConfig;
