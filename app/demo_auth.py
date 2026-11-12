"""Optional Google sign-in for the demo deployment.

Disabled unless GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, AUTH_SECRET and PUBLIC_BACKEND_URL
and FRONTEND_URL are all set. Flow (authorization code, server side):
  /auth/google/login -> Google -> /auth/google/callback -> FRONTEND_URL/auth/callback#token=...
The browser keeps the signed token and sends it where it used to send its anonymous session id.
No cookies cross sites. The client secret never leaves the backend.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["auth"])

TOKEN_PREFIX = "ca1."
TOKEN_TTL = 30 * 24 * 3600
STATE_TTL = 600
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def enabled() -> bool:
    return all(_env(n) for n in (
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "AUTH_SECRET", "PUBLIC_BACKEND_URL", "FRONTEND_URL"))


def redirect_uri() -> str:
    return _env("PUBLIC_BACKEND_URL").rstrip("/") + "/auth/google/callback"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(payload: dict) -> str:
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    mac = hmac.new(_env("AUTH_SECRET").encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(mac)}"


def _unsign(blob: str) -> dict | None:
    try:
        body, mac = blob.rsplit(".", 1)
        good = hmac.new(_env("AUTH_SECRET").encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(good, _unb64(mac)):
            return None
        data = json.loads(_unb64(body))
        if not isinstance(data, dict) or data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


def make_session_token(sub: str, email: str, name: str | None) -> str:
    return TOKEN_PREFIX + _sign({"k": "s", "sub": sub, "email": email, "name": name,
                                 "exp": int(time.time()) + TOKEN_TTL})


def identity_from_token(value: str | None) -> dict | None:
    """Return {sub,email,name} for a valid signed session token, else None."""
    if not value or not value.startswith(TOKEN_PREFIX) or not enabled():
        return None
    data = _unsign(value[len(TOKEN_PREFIX):])
    if not data or data.get("k") != "s" or not data.get("sub"):
        return None
    return data


def owner_for(value: str | None) -> str | None:
    """Owner key for an anonymous session id or a signed token. Forged tokens get no owner."""
    if not value:
        return None
    if value.startswith(TOKEN_PREFIX):
        ident = identity_from_token(value)
        return f"user:{ident['sub']}" if ident else None
    return value


async def exchange_code(code: str) -> dict:
    """Swap an authorization code for Google's identity claims. Replaced in tests."""
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        r = await client.post(GOOGLE_TOKEN, data={
            "code": code, "client_id": _env("GOOGLE_CLIENT_ID"),
            "client_secret": _env("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": redirect_uri(), "grant_type": "authorization_code"})
    if r.status_code != 200:
        raise HTTPException(400, "Google rejected the sign-in.")
    id_token = r.json().get("id_token", "")
    # Received directly from Google over TLS, so the signature check may be skipped;
    # the claims below still have to match.
    try:
        claims = json.loads(_unb64(id_token.split(".")[1]))
    except Exception:
        raise HTTPException(400, "Google returned no identity.") from None
    return claims


def _check_claims(c: dict) -> None:
    if c.get("iss") not in ("https://accounts.google.com", "accounts.google.com"):
        raise HTTPException(400, "Unexpected token issuer.")
    if c.get("aud") != _env("GOOGLE_CLIENT_ID"):
        raise HTTPException(400, "Token was not issued for this app.")
    if c.get("exp", 0) < time.time():
        raise HTTPException(400, "Token expired.")
    if not c.get("sub") or not c.get("email") or c.get("email_verified") is not True:
        raise HTTPException(400, "Google account email is not verified.")


async def _upsert_user(sub: str, email: str, name: str | None) -> None:
    from datetime import UTC, datetime

    from app.models.database import AsyncSessionLocal
    from app.models.user import User
    async with AsyncSessionLocal() as db:
        u = await db.get(User, sub)
        if u is None:
            db.add(User(id=sub, email=email[:320], name=(name or None) and name[:200]))
        else:
            u.email, u.last_login_at = email[:320], datetime.now(UTC)
            u.name = (name or None) and name[:200]
        await db.commit()


@router.get("/config")
async def auth_config():
    return {"google": enabled()}


@router.get("/google/login")
async def google_login(request: Request):
    if not enabled():
        raise HTTPException(503, "Accounts are not configured on this deployment.")
    nonce = secrets.token_urlsafe(16)
    state = _sign({"k": "o", "n": nonce, "exp": int(time.time()) + STATE_TTL})
    url = GOOGLE_AUTH + "?" + urlencode({
        "client_id": _env("GOOGLE_CLIENT_ID"), "redirect_uri": redirect_uri(),
        "response_type": "code", "scope": "openid email profile", "state": state,
        "prompt": "select_account"})
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie("oauth_nonce", nonce, max_age=STATE_TTL, httponly=True, secure=True, samesite="lax",
                    path="/auth/google")
    return resp


@router.get("/google/callback")
async def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if not enabled():
        raise HTTPException(503, "Accounts are not configured on this deployment.")
    front = _env("FRONTEND_URL").rstrip("/")
    if error or not code:
        return RedirectResponse(f"{front}/auth/callback#error=cancelled", status_code=302)
    st = _unsign(state)
    nonce = request.cookies.get("oauth_nonce", "")
    if not st or st.get("k") != "o" or not nonce or not hmac.compare_digest(str(st.get("n")), nonce):
        return RedirectResponse(f"{front}/auth/callback#error=state", status_code=302)
    claims = await exchange_code(code)
    _check_claims(claims)
    await _upsert_user(claims["sub"], claims["email"], claims.get("name"))
    token = make_session_token(claims["sub"], claims["email"], claims.get("name"))
    resp = RedirectResponse(f"{front}/auth/callback#token={token}", status_code=302)
    resp.delete_cookie("oauth_nonce", path="/auth/google")
    return resp


@router.get("/me")
async def me(request: Request):
    v = request.headers.get("x-demo-session")
    ident = identity_from_token(v)
    if not ident:
        raise HTTPException(401, "Not signed in.")
    return {"email": ident["email"], "name": ident.get("name")}
