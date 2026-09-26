import type { NextConfig } from "next";

// Browser → /api/* is forwarded to FastAPI by app/api/[...path]/route.ts, and
// server components call API_URL directly. Set API_URL on the host (e.g. the
// Render service URL); it defaults to a local API on port 8000.
const nextConfig: NextConfig = {
  // e.g. ALLOWED_DEV_ORIGINS="*.trycloudflare.com" when demoing `next dev` through a tunnel
  allowedDevOrigins: process.env.ALLOWED_DEV_ORIGINS?.split(",") ?? [],
};

export default nextConfig;
