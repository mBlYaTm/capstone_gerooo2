# alerting.py - Telegram аюулгүй байдлын мэдэгдэл
import httpx
import os
import time
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Spam хязгаарлалт: минутад дээд тал нь 5 мэдэгдэл
_last_alerts: list[float] = []


async def send_security_alert(event_type: str, ip: str, score: int, jti: str, reasons: list) -> bool:
    """HIGH эрсдлийн үед Telegram-руу мэдэгдэл илгээнэ."""
    global _last_alerts

    # Throttle: сүүлийн 60 секундэд 5-аас дээш мэдэгдэл илгээхгүй
    now = time.time()
    _last_alerts = [t for t in _last_alerts if now - t < 60]
    if len(_last_alerts) >= 5:
        return False
    _last_alerts.append(now)

    if not BOT_TOKEN or BOT_TOKEN == "your-telegram-bot-token-here":
        print(f"⚠️  Telegram тохируулаагүй. Alert: {event_type} | IP: {ip} | Score: {score}")
        return False

    message = (
        f"🚨 АЮУЛГҮЙ БАЙДЛЫН ДОХИО!\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"Үйл явдал: {event_type}\n"
        f"IP: {ip}\n"
        f"Эрсдлийн оноо: {score} (HIGH)\n"
        f"Шалтгаан: {', '.join(reasons)}\n"
        f"Арга хэмжээ: Токен устгагдсан\n"
        f"Цаг: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
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
        print(f"Telegram алдаа: {e}")
        return False
