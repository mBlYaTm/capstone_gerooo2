# alerting.py - Telegram security alerts
import httpx
import time
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")
_last_alerts: list[float] = []

async def send_security_alert(event_type: str, ip: str, score: int, jti: str, reasons: list) -> bool:
    """Send HIGH risk alert to Telegram."""
    global _last_alerts

    now = time.time()
    _last_alerts = [t for t in _last_alerts if now - t < 60]
    if len(_last_alerts) >= 5:
        return False
    _last_alerts.append(now)

    message = (
        f" SECURITY ALERT!\n"
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
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": message},
                timeout=5
            )
            return resp.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False