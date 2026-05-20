# context.py - Токеныг IP болон User-Agent-тэй холбоно
import hashlib
import time
import hmac
from fastapi import Request


def get_context_hash(request: Request) -> str:
    """
    IP + User-Agent + цагийн цонх ашиглан context hash үүсгэнэ.
    Нэг минут бүрт шинэ цонх нээгдэнэ (жижиг хазайлтыг зөвшөөрнө).
    """
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    # Минутад нэг удаа өөрчлөгдөх цагийн хэсэг
    time_window = str(int(time.time() // 60))

    raw = f"{ip}:{user_agent}:{time_window}"
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_context(stored_hash: str, request: Request) -> bool:
    """Одоогийн context-ийг хадгалсан hash-тэй харьцуулна."""
    current_hash = get_context_hash(request)
    return hmac.compare_digest(stored_hash, current_hash)
