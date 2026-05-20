# detectors.py - 4 төрлийн халдлага илрүүлэгч + эрсдлийн оноо
import redis
import time
import os
from dotenv import load_dotenv

load_dotenv()

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


class ReplayDetector:
    """
    Replay Attack илрүүлэгч.
    Нэг jti-г хоёр удаа ашиглахыг оролдвол (+30 оноо).
    """
    def check(self, jti: str) -> int:
        key = f"used_jti:{jti}"
        # nx=True: зөвхөн шинэ key байвал True буцаана
        is_new = r.set(key, "1", nx=True, ex=3600)
        if is_new:
            return 0        # Анх удаа — хэвийн
        return 30           # Дахин ашигласан — replay attack!


class VelocityDetector:
    """
    Velocity Burst илрүүлэгч.
    1 секундэд 10-аас дээш хүсэлт ирвэл (+40 оноо).
    """
    def check(self, ip: str) -> int:
        key = f"velocity:{ip}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, 1)    # Анх удаа: 1 секундийн TTL
        if count > 10:
            return 40           # Хэт хурдан — халдлага!
        return 0


class GeoImpossibilityDetector:
    """
    Geo Impossibility илрүүлэгч.
    Физикийн хувьд боломжгүй аяллыг илрүүлнэ (+50 оноо).
    Жич: GeoLite2-City.mmdb файл шаардлагатай (maxmind.com-с үнэгүй татна).
    """
    def check(self, ip: str, jti: str) -> int:
        try:
            import geoip2.database
            db_path = "GeoLite2-City.mmdb"
            if not os.path.exists(db_path):
                return 0    # DB файл байхгүй бол алгасна

            with geoip2.database.Reader(db_path) as reader:
                response = reader.city(ip)
                lat = response.location.latitude
                lon = response.location.longitude

            last_key = f"last_geo:{jti}"
            last_data = r.hgetall(last_key)

            now = time.time()
            if last_data:
                last_lat = float(last_data.get("lat", lat))
                last_lon = float(last_data.get("lon", lon))
                last_time = float(last_data.get("time", now))
                elapsed_hours = (now - last_time) / 3600

                # Хоёр цэгийн хоорондох зайг тооцно (км)
                import math
                dlat = math.radians(lat - last_lat)
                dlon = math.radians(lon - last_lon)
                a = (math.sin(dlat/2)**2 +
                     math.cos(math.radians(last_lat)) *
                     math.cos(math.radians(lat)) *
                     math.sin(dlon/2)**2)
                distance_km = 6371 * 2 * math.asin(math.sqrt(a))

                if elapsed_hours > 0:
                    speed_kmh = distance_km / elapsed_hours
                    if speed_kmh > 900:     # Нисэх онгоцноос хурдан
                        return 50

            # Одоогийн байршлыг хадгална
            r.hset(last_key, mapping={"lat": lat, "lon": lon, "time": now})
            r.expire(last_key, 86400)

        except Exception:
            pass    # IP байршил тодорхойлох боломжгүй — алгасна

        return 0


class EndpointEnumerationDetector:
    """
    Endpoint Enumeration илрүүлэгч.
    5-аас дээш 404 хуудас хайвал (+35 оноо) — хакер систем шалгаж байна.
    """
    def check(self, ip: str, path: str, status_code: int) -> int:
        if status_code != 404:
            return 0
        key = f"enum_paths:{ip}"
        r.sadd(key, path)
        r.expire(key, 3600)
        count = r.scard(key)
        if count > 5:
            return 35
        return 0


class RiskScorer:
    """
    Бүх илрүүлэгчийн оноог нэгтгэж эрсдлийн түвшин тодорхойлно.
    LOW (0-30) / MEDIUM (31-60) / HIGH (61+)
    """
    def __init__(self):
        self.replay = ReplayDetector()
        self.velocity = VelocityDetector()
        self.geo = GeoImpossibilityDetector()
        self.enum = EndpointEnumerationDetector()

    def score(self, jti: str, ip: str, path: str = "/", status: int = 200) -> dict:
        total = 0
        reasons = []

        r_score = self.replay.check(jti)
        if r_score:
            total += r_score
            reasons.append("replay_attack")

        v_score = self.velocity.check(ip)
        if v_score:
            total += v_score
            reasons.append("velocity_burst")

        g_score = self.geo.check(ip, jti)
        if g_score:
            total += g_score
            reasons.append("geo_impossibility")

        e_score = self.enum.check(ip, path, status)
        if e_score:
            total += e_score
            reasons.append("endpoint_enumeration")

        if total <= 30:
            level = "LOW"
        elif total <= 60:
            level = "MEDIUM"
        else:
            level = "HIGH"

        return {"score": total, "level": level, "reasons": reasons}
