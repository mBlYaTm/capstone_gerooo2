# alerting.py - Telegram security alerts
import httpx
import os
import threading
import time
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Spam хязгаарлалт: минутад дээд тал нь 5 мэдэгдэл
MAX_ALERTS_PER_MINUTE = 5
_last_alerts: list[float] = []
_lock = threading.Lock()


def telegram_configured() -> bool:
    """.env дотор жинхэнэ bot token, chat id тохируулсан эсэх."""
    placeholders = ("", "your-telegram-bot-token-here", "your-chat-id-here")
    return BOT_TOKEN not in placeholders and CHAT_ID not in placeholders


def _allow_alert() -> bool:
    """Сүүлийн 60 секундэд 5-аас олон мэдэгдэл илгээхгүй."""
    global _last_alerts
    now = time.time()
    with _lock:
        _last_alerts = [t for t in _last_alerts if now - t < 60]
        if len(_last_alerts) >= MAX_ALERTS_PER_MINUTE:
            return False
        _last_alerts.append(now)
        return True


def _post_to_telegram(message: str) -> bool:
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message},
            timeout=5,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def send_security_alert(event_type: str, ip: str, score: int, jti: str,
                        reasons: list, background: bool = True) -> bool:
    """
    HIGH эрсдэл / replay үед Telegram-руу мэдэгдэл илгээнэ.
    background=True үед тусдаа thread-д илгээнэ — API хариу 5 сек хүлээхгүй.
    Буцаах утга: мэдэгдэл илгээхээр явуулсан эсэх.
    """
    if not telegram_configured():
        print(f"⚠️  Telegram тохируулаагүй. Alert: {event_type} | IP: {ip} | Score: {score}")
        return False
    if not _allow_alert():
        return False

    message = (
        f"🚨 SECURITY ALERT!\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"Event: {event_type}\n"
        f"IP: {ip}\n"
        f"Risk Score: {score}\n"
        f"Reasons: {', '.join(reasons)}\n"
        f"Action: Token destroyed\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"JTI: {jti[:8]}..."
    )

    if background:
        threading.Thread(target=_post_to_telegram, args=(message,), daemon=True).start()
        return True
    return _post_to_telegram(message)
