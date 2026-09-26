// Forwards every /api/* request from the browser to the FastAPI service.
// Done in code (not a config rewrite) so it behaves the same locally and on
// Vercel: the agent's event stream is passed through unbuffered, the
// participant's session cookie is relayed both ways, and long agent turns get
// up to maxDuration seconds.
import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

const API = process.env.API_URL ?? "http://127.0.0.1:8000";
const REQUEST_HEADERS = ["cookie", "content-type", "accept", "user-agent", "x-admin-token"];
const RESPONSE_HEADERS = ["content-type", "cache-control", "content-disposition", "x-accel-buffering"];

async function forward(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const url = `${API}/api/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  for (const h of REQUEST_HEADERS) {
    const v = req.headers.get(h);
    if (v) headers.set(h, v);
  }
  headers.set("x-forwarded-proto", req.nextUrl.protocol.replace(":", ""));

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: req.method,
      headers,
      body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json({ detail: "The study server is not reachable. Please try again in a minute." }, { status: 502 });
  }

  const out = new Headers();
  for (const h of RESPONSE_HEADERS) {
    const v = upstream.headers.get(h);
    if (v) out.set(h, v);
  }
  for (const cookie of upstream.headers.getSetCookie()) out.append("set-cookie", cookie);
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { forward as GET, forward as POST, forward as PUT, forward as PATCH, forward as DELETE };
