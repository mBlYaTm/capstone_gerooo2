# context.py - Токеныг IP болон User-Agent-тэй холбоно
import hashlib
import hmac
from fastapi import Request


def get_context_hash(request: Request) -> str:
    """
    IP + User-Agent ашиглан context hash үүсгэнэ.
    Цагийн цонх оруулахгүй: өмнө нь минут солигдоход hash өөрчлөгдөж,
    хүчинтэй токен "context_drift" болж устдаг байсан. Хугацааг TTL хариуцна.
    """
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    raw = f"{ip}:{user_agent}"
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_context(stored_hash: str, request: Request) -> bool:
    """Одоогийн context-ийг хадгалсан hash-тэй харьцуулна."""
    current_hash = get_context_hash(request)
    return hmac.compare_digest(stored_hash, current_hash)
