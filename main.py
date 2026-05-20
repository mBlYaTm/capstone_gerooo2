# main.py - FastAPI application entry point
# Run command: uvicorn main:app --reload
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import secrets
import os

from token_engine import create_token, validate_token
from destruct_engine import cleanup_job, destruct_token, DestructReason
from redis_store import ping, token_exists, delete_token

# ── Background Scheduler (runs cleanup every 60 seconds) ─────────────────────
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(cleanup_job, "interval", seconds=60, id="cleanup")
    scheduler.start()
    print("✅ Scheduler started")
    yield
    scheduler.shutdown()
    print("🛑 Scheduler stopped")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Zero-Persistence Self-Destructing Token System",
    version="1.0.0",
    description="Capstone Project — API security system with automatic token invalidation",
    lifespan=lifespan,
)

# ── CORS (required for dashboard to call the API) ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Admin authentication ───────────────────────────────────────────────────────
security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, "admin")
    ok_pass = secrets.compare_digest(credentials.password, "admin123")
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return credentials.username

# ── Request/Response models ───────────────────────────────────────────────────
class TokenRequest(BaseModel):
    user_id:  str
    max_uses: int = 10

class ValidateRequest(BaseModel):
    token: str

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def dashboard():
    """Serve the dashboard HTML page"""
    html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    return FileResponse(html_path)


@app.get("/health")
async def health():
    """Check system health status"""
    redis_ok = ping()
    return {
        "status":    "ok" if redis_ok else "degraded",
        "redis":     "connected" if redis_ok else "disconnected",
        "scheduler": "running" if scheduler.running else "stopped",
        "system":    "Zero-Persistence Token System v1.0",
    }


@app.post("/request-token")
async def request_token(body: TokenRequest, request: Request):
    """
    Issue a new token.
    POST /request-token
    Body: {"user_id": "alice", "max_uses": 10}
    """
    if not ping():
        raise HTTPException(status_code=503, detail="Redis is not connected")
    result = create_token(body.user_id, request, max_uses=body.max_uses)
    return result


@app.post("/validate")
async def validate(body: ValidateRequest, request: Request):
    """
    Validate a token.
    POST /validate
    Body: {"token": "eyJ..."}
    """
    result = validate_token(body.token, request)
    if not result["valid"]:
        raise HTTPException(status_code=401, detail=result)
    return result


@app.delete("/admin/revoke/{jti}")
async def revoke_token(jti: str, admin: str = Depends(verify_admin)):
    """
    Admin manually revokes a token (5th self-destruct trigger).
    DELETE /admin/revoke/{jti}
    Basic Auth: admin / admin123
    """
    if not token_exists(jti):
        raise HTTPException(status_code=404, detail="Token not found")
    destruct_token(jti, DestructReason.ADMIN_REVOKE, extra=f"by_admin={admin}")
    return {"message": f"Token {jti[:8]}... has been revoked", "reason": "admin_revoked"}


@app.get("/admin/stats")
async def stats(admin: str = Depends(verify_admin)):
    """System statistics (admin only)."""
    from redis_store import r
    active_tokens = len(list(r.scan_iter("token:*")))
    used_jtis     = len(list(r.scan_iter("used_jti:*")))
    return {
        "active_tokens": active_tokens,
        "used_jtis":     used_jtis,
        "scheduler":     "running" if scheduler.running else "stopped",
    }