

"""
wt_utils.py - Web/token utilities for Silli Bot.

This module centralizes helpers used by the bot to:
- Mint short-lived HS256 JWTs for the auto-ingest relay (Cloudflare Worker).
- Build well-formed deep links to the PWA (host + optional subpath).
- Redact tokens in URLs before logging.

Security notes:
- Never log or print minted JWTs. Use `redact_url_token()` for any URLs that contain `tok=...`.
- Keep RELAY_SECRET only on the bot/relay side; it must never be exposed to the PWA.
"""

from __future__ import annotations

import hmac
import json
import os
import time
from base64 import urlsafe_b64encode
from hashlib import sha256
from typing import Dict, Optional
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl, ParseResult


# ------------------------------- JWT ---------------------------------


def _b64url(data: bytes) -> str:
    """Base64url encode without padding, as required by JWT."""
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def encode_jwt_hs256(payload: Dict, secret: str) -> str:
    """
    Minimal HS256 JWT encoder (no external dependencies).
    Caller is responsible for including an 'exp' (unix seconds) in payload.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
    sig_b64 = _b64url(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def mint_autoingest_token(
    *,
    chat_id: int,
    family_id: str,
    session_id: str,
    ttl_sec: int,
    relay_secret: str,
) -> str:
    """
    Build a short-lived JWT used by the PWA to POST the derived session JSON
    to the relay. The relay validates HS256 and forwards to Telegram.

    Claims:
      chat_id, family_id, session_id, exp (unix seconds)
    """
    if not relay_secret:
        raise ValueError("relay_secret is required")
    if ttl_sec <= 0:
        raise ValueError("ttl_sec must be > 0")

    exp = int(time.time()) + int(ttl_sec)
    claims = {
        "chat_id": int(chat_id),
        "family_id": str(family_id),
        "session_id": str(session_id),
        "exp": exp,
    }
    return encode_jwt_hs256(claims, relay_secret)


# ------------------------- PWA deep-linking ---------------------------


def _normalize_host_and_path(pwa_host: str, pwa_path: Optional[str]) -> ParseResult:
    """
    Accepts:
      pwa_host: either a bare host (e.g., 'example.com') or a full URL ('https://example.com')
      pwa_path: optional subpath like '/silli-meter'
    Returns a parsed URL with https scheme and normalized path.
    """
    # If host already includes scheme, parse it; else construct an https URL
    if "://" in pwa_host:
        parsed = urlparse(pwa_host)
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc or parsed.path  # handle 'https://example.com'
        base_path = parsed.path or ""
    else:
        scheme = "https"
        netloc = pwa_host
        base_path = ""

    # Normalize subpath
    p = (pwa_path or "").strip()
    if p and not p.startswith("/"):
        p = "/" + p

    full_path = (base_path.rstrip("/") + p).rstrip("/") or ""
    return ParseResult(scheme=scheme, netloc=netloc, path=full_path, params="", query="", fragment="")


def build_pwa_deeplink(
    *,
    pwa_host: str,
    pwa_path: Optional[str],
    mode: str,
    family_id: str,
    session_id: str,
    token: Optional[str] = None,
    dyad: str = "night",
    extra_params: Optional[Dict[str, str]] = None,
) -> str:
    """
    Construct a stable, https deep link to the PWA with required query params.
    If `token` is provided, it is appended as `tok=...`.

    Example:
      build_pwa_deeplink(
          pwa_host="purplewarren.github.io",
          pwa_path="/silli-meter",
          mode="helper",
          family_id="fam_123",
          session_id="fam_123_20250805_190500",
          token="eyJhbGciOi..."
      )
    """
    base = _normalize_host_and_path(pwa_host, pwa_path)
    params: Dict[str, str] = {
        "mode": mode,
        "family": family_id,
        "session": session_id,
        "dyad": dyad,
    }
    if token:
        params["tok"] = token
    if extra_params:
        params.update({k: str(v) for k, v in extra_params.items()})

    query = urlencode(params, doseq=False)
    return urlunparse(base._replace(query=query))


def redact_url_token(url: str, repl: str = "REDACTED") -> str:
    """
    Replace the value of `tok` in a URL with a redacted marker for safe logging.
    """
    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "tok" in q:
        q["tok"] = repl
    return urlunparse(parsed._replace(query=urlencode(q)))


# ------------------------------ Env ----------------------------------


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch environment variable with an optional default (avoid crashes in handlers)."""
    return os.getenv(name, default)


__all__ = [
    "encode_jwt_hs256",
    "mint_autoingest_token",
    "build_pwa_deeplink",
    "redact_url_token",
    "get_env",
]