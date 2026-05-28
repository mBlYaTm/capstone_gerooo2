# main.py - FastAPI application entry point
from contextlib import asynccontextmanager
import asyncio, json, time, secrets, os

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

from token_engine import create_token, validate_token
from destruct_engine import cleanup_job, destruct_token, DestructReason
from redis_store import ping, token_exists, delete_token, r as redis_client

# ── SSE Event Queue ───────────────────────────────────────────────────────────
_sse_clients: list[asyncio.Queue] = []

def broadcast_event(event_type: str, data: dict):
    """Send real-time event to all SSE clients."""
    msg = json.dumps({"type": event_type, "data": data, "time": time.strftime('%H:%M:%S')})
    dead = []
    for q in _sse_clients:
        try:
            q.put_nowait(msg)
        except:
            dead.append(q)
    for q in dead:
        _sse_clients.remove(q)

# ── Scheduler ────────────────────────────────────────────────────────────────
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(cleanup_job, "interval", seconds=60, id="cleanup")
    scheduler.start()
    print("✅ Scheduler started")
    broadcast_event("log", {"msg": "Scheduler started", "level": "ok"})
    yield
    scheduler.shutdown()
    print("🛑 Scheduler stopped")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Zero-Persistence Self-Destructing Token System",
    version="1.0.0",
    description="Capstone Project — API security system with automatic token invalidation",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Security Headers Middleware ───────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # OWASP ZAP-н олдсон 4 асуудлыг засна
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["X-XSS-Protection"]        = "1; mode=block"
    response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]      = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# ── Rate Limiting Middleware ──────────────────────────────────────────────────
RATE_LIMIT          = 200   # max requests
RATE_WINDOW_SECONDS = 60   # per 60 seconds

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for dashboard and SSE
    if request.url.path in ["/", "/events", "/health"]:
        return await call_next(request)

    ip  = request.client.host if request.client else "unknown"
    key = f"ratelimit:{ip}"

    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, RATE_WINDOW_SECONDS)

        # Add rate limit headers
        remaining = max(0, RATE_LIMIT - count)

        if count > RATE_LIMIT:
            broadcast_event("log", {
                "msg":   f"Rate limit exceeded — IP: {ip} ({count} requests)",
                "level": "err"
            })
            response = Response(
                content=json.dumps({"detail": "Rate limit exceeded. Try again later."}),
                status_code=429,
                media_type="application/json"
            )
            response.headers["X-RateLimit-Limit"]     = str(RATE_LIMIT)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["Retry-After"]           = str(RATE_WINDOW_SECONDS)
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    except Exception:
        return await call_next(request)

# ── Auth ──────────────────────────────────────────────────────────────────────
security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok = secrets.compare_digest(credentials.username, "admin") and \
         secrets.compare_digest(credentials.password, "admin123")
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return credentials.username

# ── Models ────────────────────────────────────────────────────────────────────
class TokenRequest(BaseModel):
    user_id:  str
    max_uses: int = 10

class ValidateRequest(BaseModel):
    token: str

# ── SSE Endpoint ──────────────────────────────────────────────────────────────
@app.get("/events")
async def sse_events(request: Request):
    """Server-Sent Events — real-time dashboard updates."""
    queue = asyncio.Queue()
    _sse_clients.append(queue)

    async def event_stream():
        try:
            yield f"data: {json.dumps({'type':'connected','time':time.strftime('%H:%M:%S')})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type':'ping'})}\n\n"
        finally:
            if queue in _sse_clients:
                _sse_clients.remove(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", 
                 "Connection": "close"})

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
async def dashboard():
    return FileResponse(os.path.join(os.path.dirname(__file__), "dashboard.html"))

@app.get("/health")
async def health():
    redis_ok = ping()
    return {
        "status":    "ok" if redis_ok else "degraded",
        "redis":     "connected" if redis_ok else "disconnected",
        "scheduler": "running" if scheduler.running else "stopped",
        "system":    "Zero-Persistence Token System v1.0",
    }

@app.post("/request-token")
async def request_token(body: TokenRequest, request: Request):
    if not ping():
        raise HTTPException(status_code=503, detail="Redis is not connected")
    result = create_token(body.user_id, request, max_uses=body.max_uses)
    broadcast_event("log", {"msg": f"Token issued — {body.user_id} — {result['jti'][:8]}…", "level": "ok"})
    return result

@app.post("/validate")
async def validate(body: ValidateRequest, request: Request):
    result = validate_token(body.token, request)
    if not result["valid"]:
        reason = result.get("reason", "unknown")
        risk   = result.get("risk", {})
        broadcast_event("log", {"msg": f"Token rejected — {reason}", "level": "err"})

        if reason == "high_risk_detected" and risk:
            ip = request.client.host if request.client else "unknown"
            broadcast_event("telegram_alert", {
                "event":   "Anomaly HIGH Risk",
                "ip":      ip,
                "score":   risk.get("score", 0),
                "reasons": risk.get("reasons", []),
                "jti":     result.get("jti", "")[:8] + "…"
            })
            broadcast_event("detector_fired", {
                "reasons": risk.get("reasons", []),
                "score":   risk.get("score", 0),
                "level":   risk.get("level", "HIGH")
            })

        raise HTTPException(status_code=401, detail=result)

    broadcast_event("log", {"msg": f"Token valid — uses left: {result.get('uses_left','?')}", "level": "ok"})
    return result

@app.delete("/admin/revoke/{jti}")
async def revoke_token(jti: str, admin: str = Depends(verify_admin)):
    if not token_exists(jti):
        raise HTTPException(status_code=404, detail="Token not found")
    destruct_token(jti, DestructReason.ADMIN_REVOKE, extra=f"by_admin={admin}")
    broadcast_event("log", {"msg": f"Admin revoked — {jti[:8]}…", "level": "wrn"})
    return {"message": f"Token {jti[:8]}... has been revoked", "reason": "admin_revoked"}

@app.get("/admin/stats")
async def stats(admin: str = Depends(verify_admin)):
    active_tokens = len(list(redis_client.scan_iter("token:*")))
    used_jtis     = len(list(redis_client.scan_iter("used_jti:*")))
    return {
        "active_tokens": active_tokens,
        "used_jtis":     used_jtis,
        "scheduler":     "running" if scheduler.running else "stopped",
    }