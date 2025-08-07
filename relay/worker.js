

// Silli Auto‑Ingest Relay (Cloudflare Worker)
// Purpose: accept a derived‑only PWA session JSON and forward it to our Telegram bot
// WITHOUT exposing the bot token to the browser.
//
// Endpoint: POST /ingest
//   Headers: Authorization: Bearer <JWT>
//   Body:    JSON (the PWA session report; derived metrics only)
//
// JWT (HS256) claims required:
//   chat_id, family_id, session_id, exp (unix seconds)
//
// Required Worker secrets (set via `wrangler secret put ...`):
//   RELAY_SECRET  - HMAC key to verify JWT (shared with bot only)
//   BOT_TOKEN     - Telegram bot token (server-side only; never exposed to the PWA)

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders()
      });
    }

    // Auto-ingest from PWA (JWT in Authorization: Bearer <tok>)
    if (url.pathname === '/ingest' && request.method === 'POST') {
      return handleIngest(request, env);
    }

    // Bot pulls pending sessions (X-Auth: <RELAY_SECRET>)
    if (url.pathname === '/pull' && request.method === 'GET') {
      return handlePull(request, env);
    }

    return new Response('Not found', { status: 404, headers: corsHeaders() });
  }
};

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-Auth',
  };
}

async function handleIngest(request, env) {
  try {
    const auth = request.headers.get('authorization') || '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : null;
    if (!token) return json({ error: 'missing bearer' }, 401);

    // Minimal HS256 verification (same RELAY_SECRET as bot)
    const claims = await verifyJwtHS256(token, env.RELAY_SECRET);
    if (!claims) return json({ error: 'invalid token' }, 401);

    const body = await request.json();
    const chatId = String(claims.chat_id);
    const sessionId = String(claims.session_id);

    // Store session JSON in KV
    const key = `session:${chatId}:${sessionId}`;
    await env.SILLI_SESSIONS.put(key, JSON.stringify(body), { expirationTtl: 60 * 60 * 24 * 7 }); // 7d

    // Append to pending list
    const listKey = `pending:${chatId}`;
    const existing = await env.SILLI_SESSIONS.get(listKey, 'json') || [];
    existing.push(key);
    await env.SILLI_SESSIONS.put(listKey, JSON.stringify(existing), { expirationTtl: 60 * 60 * 24 * 7 });

    return json({ ok: true, stored: key });
  } catch (e) {
    return json({ ok: false, error: String(e) }, 500);
  }
}

async function handlePull(request, env) {
  const url = new URL(request.url);
  const auth = request.headers.get('x-auth') || request.headers.get('X-Auth') || '';
  if (!auth || auth !== env.RELAY_SECRET) {
    return json({ error: 'unauthorized' }, 401);
  }

  const chatId = url.searchParams.get('chat_id');
  const limit = parseInt(url.searchParams.get('limit') || '5', 10);
  if (!chatId) return json({ error: 'missing chat_id' }, 400);

  const listKey = `pending:${chatId}`;
  const pending = (await env.SILLI_SESSIONS.get(listKey, 'json')) || [];
  if (!pending.length) return json({ ok: true, items: [] });

  const take = pending.splice(0, Math.max(1, Math.min(limit, 10)));
  await env.SILLI_SESSIONS.put(listKey, JSON.stringify(pending), { expirationTtl: 60 * 60 * 24 * 7 });

  const items = [];
  for (const key of take) {
    const raw = await env.SILLI_SESSIONS.get(key);
    if (raw) items.push({ key, data: JSON.parse(raw) });
    // (Optional) delete after pull:
    await env.SILLI_SESSIONS.delete(key);
  }
  return json({ ok: true, items });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { 'content-type': 'application/json', ...corsHeaders() } });
}

// ----- JWT verify HS256 (matching bot's signer) -----
async function verifyJwtHS256(token, secret) {
  try {
    const [h, p, s] = token.split('.');
    const encoder = new TextEncoder();
    const data = encoder.encode(`${h}.${p}`);
    const key = await crypto.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    const sig = await crypto.subtle.sign('HMAC', key, data);
    const expected = b64url(sig);
    if (expected !== s) return null;
    const payload = JSON.parse(atobUrl(p));
    if (payload.exp && Date.now() / 1000 > payload.exp) return null;
    return payload;
  } catch {
    return null;
  }
}
function b64url(buf) {
  let s = btoa(String.fromCharCode(...new Uint8Array(buf)));
  return s.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function atobUrl(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  const pad = s.length % 4 ? 4 - (s.length % 4) : 0;
  return atob(s + '='.repeat(pad));
}