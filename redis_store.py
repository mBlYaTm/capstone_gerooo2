# redis_store.py - Redis дээр токен хадгалах, устгах
import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Redis-тэй холболт үүсгэнэ
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


def store_token(jti: str, ctx_hash: str, ttl: int = 300, max_uses: int = 10) -> bool:
    """Токений мэдээллийг Redis-д хадгална."""
    pipe = r.pipeline()
    pipe.hset(f"token:{jti}", mapping={
        "ctx_hash": ctx_hash,
        "max_uses": max_uses,
        "use_count": 0,
        "status": "active"
    })
    pipe.expire(f"token:{jti}", ttl)
    pipe.execute()
    return True


def get_token_data(jti: str) -> dict | None:
    """Redis-аас токений мэдээллийг авна."""
    data = r.hgetall(f"token:{jti}")
    if not data:
        return None
    return data


def increment_use_count(jti: str) -> int:
    """Токений ашиглалтын тоог нэмэгдүүлнэ."""
    return r.hincrby(f"token:{jti}", "use_count", 1)


def delete_token(jti: str) -> bool:
    """Токеныг Redis-аас устгана (self-destruct)."""
    deleted = r.delete(f"token:{jti}")
    return deleted > 0


def token_exists(jti: str) -> bool:
    """Токен байгаа эсэхийг шалгана."""
    return r.exists(f"token:{jti}") > 0


def mark_jti_used(jti: str) -> bool:
    """jti-г ашигласан гэж тэмдэглэнэ (replay attack сэргийлэх)."""
    key = f"used_jti:{jti}"
    result = r.set(key, "1", nx=True, ex=3600)  # nx=True: зөвхөн шинэ key байвал
    return result is True  # False = аль хэдийн ашигласан = replay attack!


def ping() -> bool:
    """Redis холболт ажиллаж байгаа эсэхийг шалгана."""
    try:
        return r.ping()
    except Exception:
        return False
