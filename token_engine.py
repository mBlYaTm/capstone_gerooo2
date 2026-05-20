# token_engine.py - Токен үүсгэх болон баталгаажуулах гол логик
import uuid
import time
import os
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

risk_scorer = RiskScorer()


def create_token(user_id: str, request: Request, max_uses: int = MAX_USES) -> dict:
    """
    Шинэ токен үүсгэнэ:
    1. jti (уникаль ID) үүсгэнэ
    2. ctx_hash (context hash) тооцно
    3. JWT гарын үсэг зурна
    4. Redis-д хадгална
    """
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

    # Redis-д хадгална (жинхэнэ токен биш, зөвхөн metadata)
    store_token(jti, ctx_hash, ttl=TTL, max_uses=max_uses)

    return {
        "token":      token,
        "expires_in": TTL,
        "jti":        jti,
    }


def validate_token(token: str, request: Request) -> dict:
    """
    Токен баталгаажуулалтын 6 алхам:
    1. JWT гарын үсэг шалгана
    2. Redis-д байгаа эсэх шалгана
    3. Context (IP/device) шалгана
    4. Ашиглалтын тоо шалгана
    5. Эрсдлийн оноо шалгана
    6. Ашиглалтын тоог нэмэгдүүлнэ
    """
    # 1. JWT decode
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        return {"valid": False, "reason": f"invalid_jwt: {str(e)}"}

    jti      = payload.get("jti")
    max_uses = payload.get("max_uses", MAX_USES)
    stored_ctx = payload.get("ctx_hash", "")

    # 2. Redis-д байгаа эсэх (TTL дуусвал автоматаар устдаг)
    if not token_exists(jti):
        return {"valid": False, "reason": "token_not_found_or_expired"}

    # 3. Context шалгалт (IP/device өөрчлөгдсөн эсэх)
    if not verify_context(stored_ctx, request):
        destruct_token(jti, DestructReason.CONTEXT_DRIFT,
                       extra=f"ip={request.client.host}")
        return {"valid": False, "reason": "context_drift_detected"}

    # 4. Ашиглалтын тоо шалгалт
    token_data = get_token_data(jti)
    use_count  = int(token_data.get("use_count", 0))
    if use_count >= max_uses:
        destruct_token(jti, DestructReason.MAX_USES, extra=f"uses={use_count}")
        return {"valid": False, "reason": "max_uses_exceeded"}

    # 5. Эрсдлийн оноо шалгалт
    ip     = request.client.host if request.client else "unknown"
    risk   = risk_scorer.score(jti, ip)
    if risk["level"] == "HIGH":
        destruct_token(jti, DestructReason.HIGH_RISK,
                       extra=f"score={risk['score']},reasons={risk['reasons']}")
        return {"valid": False, "reason": "high_risk_detected", "risk": risk}

    # 6. Ашиглалтын тоог нэмэгдүүлнэ
    new_count = increment_use_count(jti)

    return {
        "valid":     True,
        "jti":       jti,
        "uses_left": max_uses - new_count,
        "risk":      risk,
    }
