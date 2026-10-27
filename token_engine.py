# token_engine.py - Token creation and validation logic
import uuid
import time
import os
from jose import jwt, JWTError
from fastapi import Request
from dotenv import load_dotenv

from redis_store import store_token, consume_use, token_exists
from context import get_context_hash, verify_context
from detectors import RiskScorer, ReplayDetector
from destruct_engine import destruct_token, log_security_event, DestructReason
from alerting import send_security_alert

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-please")
ALGORITHM  = "HS256"
TTL        = int(os.getenv("TOKEN_TTL_SECONDS", 300))
MAX_USES   = int(os.getenv("MAX_USES_DEFAULT", 10))

risk_scorer = RiskScorer()
replay_detector = ReplayDetector()


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
    ip = request.client.host if request.client else "unknown"

    # Step 1: JWT decode
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        return {"valid": False, "reason": f"invalid_jwt: {str(e)}"}

    jti        = payload.get("jti")
    max_uses   = payload.get("max_uses", MAX_USES)
    stored_ctx = payload.get("ctx_hash", "")

    # Step 2: Check Redis — устгагдсан токен дахин ирвэл replay attack
    if not token_exists(jti):
        replay_score = replay_detector.check(jti)
        if replay_score:
            risk = {"score": replay_score, "level": "HIGH", "reasons": ["replay_attack"]}
            log_security_event(f"REPLAY_ATTACK | jti={jti} | ip={ip}")
            send_security_alert(
                event_type="Replay of destroyed token",
                ip=ip,
                score=replay_score,
                jti=jti,
                reasons=risk["reasons"],
            )
            return {"valid": False, "reason": "replay_detected", "jti": jti, "risk": risk}
        return {"valid": False, "reason": "token_not_found_or_expired"}

    # Step 3: Context check
    if not verify_context(stored_ctx, request):
        destruct_token(jti, DestructReason.CONTEXT_DRIFT, extra=f"ip={ip}")
        return {"valid": False, "reason": "context_drift_detected"}

    # Step 4: Risk score check
    risk = risk_scorer.score(jti, ip)
    if risk["level"] == "HIGH":
        destruct_token(jti, DestructReason.HIGH_RISK,
                       extra=f"score={risk['score']},reasons={risk['reasons']}")
        send_security_alert(
            event_type="Anomaly HIGH Risk",
            ip=ip,
            score=risk["score"],
            jti=jti,
            reasons=risk["reasons"],
        )
        return {"valid": False, "reason": "high_risk_detected", "jti": jti, "risk": risk}

    # Step 5: Max uses — шалгах ба нэмэхийг нэг atomic алхмаар хийнэ
    new_count = consume_use(jti)
    if new_count == -1:
        # Шалгалтын явцад TTL дууссан эсвэл өөр хүсэлт устгасан
        return {"valid": False, "reason": "token_not_found_or_expired"}
    if new_count > max_uses:
        destruct_token(jti, DestructReason.MAX_USES, extra=f"uses={new_count}")
        return {"valid": False, "reason": "max_uses_exceeded"}

    # Step 6: Сүүлчийн ашиглалт бол хүсэлтийг зөвшөөрөөд токеныг шууд устгана
    if new_count == max_uses:
        destruct_token(jti, DestructReason.MAX_USES, extra=f"uses={new_count},final_use")

    return {
        "valid":     True,
        "jti":       jti,
        "uses_left": max_uses - new_count,
        "risk":      risk,
    }
