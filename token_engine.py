# token_engine.py - Token creation and validation logic
import uuid
import time
import os
import httpx
from jose import jwt, JWTError
from fastapi import Request
from dotenv import load_dotenv

from crypto_utils import hash_token
from redis_store import store_token, get_token_data, increment_use_count, token_exists
from context import get_context_hash, verify_context
from detectors import RiskScorer
from destruct_engine import destruct_token, DestructReason

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-please")
ALGORITHM  = "HS256"
TTL        = int(os.getenv("TOKEN_TTL_SECONDS", 300))
MAX_USES   = int(os.getenv("MAX_USES_DEFAULT", 10))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","8890519843:AAFpy-F3I4XQUzsVvoMt2HGrE_tkHEg_UaU")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","7530616115")

risk_scorer = RiskScorer()


def send_telegram_sync(event_type: str, ip: str, score: int, jti: str, reasons: list):
    """Telegram мэдэгдэл синхрон аргаар илгээнэ."""
    message = (
        f"🚨 SECURITY ALERT!\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"Event: {event_type}\n"
        f"IP: {ip}\n"
        f"Risk Score: {score} (HIGH)\n"
        f"Reasons: {', '.join(reasons)}\n"
        f"Action: Token destroyed\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"JTI: {jti[:8]}..."
    )
    try:
        with httpx.Client() as client:
            client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": message},
                timeout=5
            )
    except Exception as e:
        print(f"Telegram error: {e}")


def create_token(user_id: str, request: Request, max_uses: int = MAX_USES) -> dict:
    """Create a new token and store in Redis."""
    jti = str(uuid.uuid4())
    ctx_hash = get_context_hash(request)
    now = int(time.time())

    payload = {
        "jti":      jti,
        "sub":      user_id,
        "iat":      now,
        "exp":      now + TTL,
        "ctx_hash": ctx_hash,
        "max_uses": max_uses,
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    store_token(jti, ctx_hash, ttl=TTL, max_uses=max_uses)

    return {
        "token":      token,
        "expires_in": TTL,
        "jti":        jti,
    }


def validate_token(token: str, request: Request) -> dict:
    """Validate token through 6-step verification pipeline."""

    # Step 1: JWT decode
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        return {"valid": False, "reason": f"invalid_jwt: {str(e)}"}

    jti        = payload.get("jti")
    max_uses   = payload.get("max_uses", MAX_USES)
    stored_ctx = payload.get("ctx_hash", "")

    # Step 2: Check Redis
    if not token_exists(jti):
        return {"valid": False, "reason": "token_not_found_or_expired"}

    # Step 3: Context check
    if not verify_context(stored_ctx, request):
        destruct_token(jti, DestructReason.CONTEXT_DRIFT,
                       extra=f"ip={request.client.host}")
        return {"valid": False, "reason": "context_drift_detected"}

    # Step 4: Max uses check
    token_data = get_token_data(jti)
    use_count  = int(token_data.get("use_count", 0))
    if use_count >= max_uses:
        destruct_token(jti, DestructReason.MAX_USES, extra=f"uses={use_count}")
        return {"valid": False, "reason": "max_uses_exceeded"}

    # Step 5: Risk score check
    ip   = request.client.host if request.client else "unknown"
    risk = risk_scorer.score(jti, ip)
    if risk["level"] == "HIGH":
        destruct_token(jti, DestructReason.HIGH_RISK,
                       extra=f"score={risk['score']},reasons={risk['reasons']}")
        # Синхрон Telegram мэдэгдэл — asyncio шаардлагагүй
        send_telegram_sync(
            event_type="Anomaly HIGH Risk",
            ip=ip,
            score=risk["score"],
            jti=jti,
            reasons=risk["reasons"]
        )
        return {"valid": False, "reason": "high_risk_detected", "risk": risk}

    # Step 6: Increment use counter
    new_count = increment_use_count(jti)

    return {
        "valid":     True,
        "jti":       jti,
        "uses_left": max_uses - new_count,
        "risk":      risk,
    }