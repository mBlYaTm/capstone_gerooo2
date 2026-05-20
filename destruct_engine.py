# destruct_engine.py - 5 нөхцөлт автомат устгалтын систем
import logging
import time
from enum import Enum
from redis_store import delete_token, r

# Бүх устгалтын үйл явдлыг файлд бичнэ
logging.basicConfig(
    filename="destruct_events.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class DestructReason(Enum):
    TTL_EXPIRED      = "ttl_expired"         # Redis TTL дуусав
    CONTEXT_DRIFT    = "context_drift"       # IP/Device өөрчлөгдөв
    MAX_USES         = "max_uses_exceeded"   # Дээд ашиглалтын тоо хэтэрсэн
    HIGH_RISK        = "anomaly_high_risk"   # Эрсдлийн оноо HIGH
    ADMIN_REVOKE     = "admin_revoked"       # Админ гараар устгав


def destruct_token(jti: str, reason: DestructReason, extra: str = "") -> bool:
    """
    Токеныг Redis-аас устгаад лог бичнэ.
    Бүх 5 trigger энэ функцийг дуудна.
    """
    success = delete_token(jti)
    msg = f"TOKEN_DESTRUCTED | jti={jti} | reason={reason.value}"
    if extra:
        msg += f" | info={extra}"
    logger.warning(msg)
    print(f"🔴 {msg}")
    return success


def cleanup_job():
    """
    APScheduler 60 секунд бүр дуудна.
    Хуучирсан velocity болон enum key-үүдийг цэвэрлэнэ.
    """
    cleaned = 0
    # Хуучирсан enum key-үүд
    for key in r.scan_iter("enum_paths:*"):
        if r.ttl(key) == -1:    # TTL тохируулаагүй
            r.expire(key, 3600)
            cleaned += 1
    logger.info(f"Cleanup job: {cleaned} keys fixed | time={time.strftime('%Y-%m-%d %H:%M:%S')}")
