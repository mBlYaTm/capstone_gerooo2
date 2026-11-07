# attack_demo.py - Dashboard-ын "Attack" табнаас дуудагддаг халдлагын жишээнүүд.
# haldlaga.sh-тай ижил 6 сценари, гэхдээ bash+curl-ийн оронд httpx-ээр өөрийн
# API руу бодит HTTP хүсэлт илгээдэг тул context binding / risk scorer /
# replay detector бүгд жинхэнэ дамжаагаараа ажиллана (dashboard-ын Event Log,
# Security Monitor, Telegram Alert Feed дээр бодитоор харагдана).
#
# lang="mn" (Монгол, default) эсвэл lang="ko" (Солонгос) — нарратив текст хоёр
# хэлээр бэлэн, HTTP дуудлагын логик хэлнээс үл хамаарч ижил ажиллана.
import asyncio
import base64
import json

import httpx

from redis_store import reset_demo_counters

API = "http://localhost:8000"
# User-Agent HTTP толгой тул зөвхөн ASCII байх ёстой — орчуулгыг narration текстэд бичнэ.
VICTIM_UA = "Mozilla/5.0 Chrome/120 (Victim-Laptop)"
HACKER_UA = "sqlmap/1.7 (Hacker-PC)"


async def _new_token(client: httpx.AsyncClient, user_id: str, max_uses: int, ua: str) -> dict:
    r = await client.post(f"{API}/request-token", json={"user_id": user_id, "max_uses": max_uses},
                           headers={"User-Agent": ua})
    return r.json()


async def _validate(client: httpx.AsyncClient, token: str, ua: str):
    r = await client.post(f"{API}/validate", json={"token": token}, headers={"User-Agent": ua})
    return r.status_code, r.json()


def _fmt_result(status: int, data: dict, lang: str) -> str:
    ok_word = {"mn": "✅ ЗӨВШӨӨРСӨН", "ko": "✅ 허용됨"}[lang]
    blocked_word = {"mn": "❌ ХААСАН", "ko": "❌ 차단됨"}[lang]
    reason_word = {"mn": "шалтгаан", "ko": "사유"}[lang]
    score_word = {"mn": "оноо", "ko": "점수"}[lang]
    uses_word = {"mn": "uses_left", "ko": "남은 횟수"}[lang]

    if status == 200 and data.get("valid"):
        return f"{ok_word}  {uses_word}={data.get('uses_left')}"
    detail = data.get("detail", data) if isinstance(data, dict) else data
    reason = detail.get("reason", str(detail)) if isinstance(detail, dict) else str(detail)
    risk = detail.get("risk") if isinstance(detail, dict) else None
    extra = f"  {score_word}={risk['score']} {risk['reasons']}" if risk else ""
    return f"{blocked_word}  {reason_word}={reason[:60]}{extra}"


def _step(who: str, text: str) -> dict:
    return {"who": who, "text": text}


async def attack_stolen(lang: str = "mn") -> list[dict]:
    T = {
        "mn": dict(got="Хохирогч (bat) токен авлаа.",
                   victim_ok="Хохирогч өөрөө ашиглав:  ",
                   stole="Токеныг хулгайлж авлаа: {tok}...",
                   hacker_try="Хакер өөр төхөөрөмжөөс:  ",
                   victim_again="Хохирогч дахин:          ",
                   end="Токен өөр төхөөрөмж (User-Agent) дээр гарч ирэнгүүт ШУУД устгагдлаа. "
                       "Хулгайлсан токен ямар ч үнэ цэнэгүй болсон."),
        "ko": dict(got="피해자(bat)가 토큰을 발급받았습니다.",
                   victim_ok="피해자 본인이 사용:  ",
                   stole="토큰을 탈취했습니다: {tok}...",
                   hacker_try="해커가 다른 기기에서:  ",
                   victim_again="피해자가 다시 시도:  ",
                   end="토큰이 다른 기기(User-Agent)에서 사용되는 순간 즉시 소멸되었습니다. "
                       "탈취된 토큰은 더 이상 쓸모가 없습니다."),
    }[lang]
    steps = []
    async with httpx.AsyncClient(timeout=10) as client:
        res = await _new_token(client, "bat", 10, VICTIM_UA)
        token = res["token"]
        steps.append(_step("system", T["got"]))
        s, d = await _validate(client, token, VICTIM_UA)
        steps.append(_step("victim", T["victim_ok"] + _fmt_result(s, d, lang)))
        steps.append(_step("hacker", T["stole"].format(tok=token[:40])))
        s, d = await _validate(client, token, HACKER_UA)
        steps.append(_step("hacker", T["hacker_try"] + _fmt_result(s, d, lang)))
        s, d = await _validate(client, token, VICTIM_UA)
        steps.append(_step("victim", T["victim_again"] + _fmt_result(s, d, lang)))
        steps.append(_step("system", T["end"]))
    return steps


async def attack_forge(lang: str = "mn") -> list[dict]:
    T = {
        "mn": dict(change="Токены доторх хэрэглэгчийг 'hacker' → 'admin' болгож өөрчиллөө.",
                   sent="Хуурамч токен илгээв: ",
                   end="JWT гарын үсэг (HS256) таарахгүй байна. Нууц түлхүүргүйгээр токеныг хуурамчаар хийх боломжгүй."),
        "ko": dict(change="토큰 내부의 사용자를 'hacker' → 'admin'으로 변조했습니다.",
                   sent="위조된 토큰을 전송: ",
                   end="JWT 서명(HS256)이 일치하지 않습니다. 비밀 키 없이는 토큰을 위조할 수 없습니다."),
    }[lang]
    steps = []
    async with httpx.AsyncClient(timeout=10) as client:
        res = await _new_token(client, "hacker", 10, HACKER_UA)
        token = res["token"]

        h, p, sig = token.split(".")

        def b64d(x: str) -> bytes:
            return base64.urlsafe_b64decode(x + "=" * (-len(x) % 4))

        def b64e(x: bytes) -> str:
            return base64.urlsafe_b64encode(x).decode().rstrip("=")

        data = json.loads(b64d(p))
        data["sub"] = data["user_id"] = "admin"
        fake = f"{h}.{b64e(json.dumps(data).encode())}.{sig}"

        steps.append(_step("hacker", T["change"]))
        st, d = await _validate(client, fake, HACKER_UA)
        steps.append(_step("hacker", T["sent"] + _fmt_result(st, d, lang)))
        steps.append(_step("system", T["end"]))
    return steps


async def attack_replay(lang: str = "mn") -> list[dict]:
    T = {
        "mn": dict(used="Хохирогч 1 удаа ашиглав (токен устна): ",
                   found="Хуучин токен олдлоо, дахин илгээе!",
                   retry="Хакерын оролдлого: ",
                   end="Устсан токены дугаар (jti) 'шатаагдсан' жагсаалтад байна → "
                       "Replay гэрэл улаан, Telegram alert явлаа. 👉 Дашбоардыг харна уу!"),
        "ko": dict(used="피해자가 1회 사용(토큰 소멸): ",
                   found="오래된 토큰을 발견, 다시 전송하자!",
                   retry="해커의 재사용 시도: ",
                   end="소멸된 토큰의 ID(jti)는 '소멸 목록'에 남아 있습니다 → "
                       "Replay 표시등이 켜지고 Telegram 알림이 전송되었습니다. 👉 대시보드를 확인하세요!"),
    }[lang]
    steps = []
    async with httpx.AsyncClient(timeout=10) as client:
        res = await _new_token(client, "tsetseg", 1, VICTIM_UA)
        token = res["token"]
        s, d = await _validate(client, token, VICTIM_UA)
        steps.append(_step("victim", T["used"] + _fmt_result(s, d, lang)))
        steps.append(_step("hacker", T["found"]))
        s, d = await _validate(client, token, VICTIM_UA)
        steps.append(_step("hacker", T["retry"] + _fmt_result(s, d, lang)))
        steps.append(_step("system", T["end"]))
    return steps


async def attack_scan(lang: str = "mn") -> list[dict]:
    T = {
        "mn": dict(scanning="Нууц хуудас хайж байна...",
                   get_line="   GET /{p} → {code}",
                   after_scan="6 өөр 404 → Endpoint Enumeration +35 оноо (MEDIUM)",
                   fast="Одоо маш хурдан дайрна!",
                   hit="{i}-р хүсэлт: ",
                   miss="HIGH хүрсэнгүй — дахин оролдоно уу (Reset дараад дахин товч дарна уу).",
                   end="35 (скан) + 40 (хурд) = 75 ≥ 61 → HIGH → токен устаж, админд Telegram alert очлоо."),
        "ko": dict(scanning="숨겨진 경로를 탐색 중...",
                   get_line="   GET /{p} → {code}",
                   after_scan="6개의 서로 다른 404 → Endpoint Enumeration +35점 (MEDIUM)",
                   fast="이제 빠르게 연속 공격합니다!",
                   hit="{i}번째 요청: ",
                   miss="HIGH에 도달하지 못했습니다 — 초기화 후 다시 눌러보세요.",
                   end="35점(스캔) + 40점(속도) = 75점 ≥ 61 → HIGH → 토큰이 소멸되고 관리자에게 Telegram 알림이 전송되었습니다."),
    }[lang]
    steps = []
    reset_demo_counters()
    async with httpx.AsyncClient(timeout=10) as client:
        res = await _new_token(client, "hacker2", 50, HACKER_UA)
        token = res["token"]
        steps.append(_step("hacker", T["scanning"]))
        for path in ("admin", "backup", ".env", "config", "wp-login.php", "phpmyadmin"):
            r = await client.get(f"{API}/{path}", headers={"User-Agent": HACKER_UA})
            steps.append(_step("hacker", T["get_line"].format(p=path, code=r.status_code)))
        steps.append(_step("system", T["after_scan"]))
        steps.append(_step("hacker", T["fast"]))

        results = await asyncio.gather(
            *[client.post(f"{API}/validate", json={"token": token}, headers={"User-Agent": HACKER_UA})
              for _ in range(20)],
            return_exceptions=True,
        )
        found = False
        for i, r in enumerate(results, 1):
            if isinstance(r, Exception):
                continue
            d = r.json()
            if "high_risk" in json.dumps(d):
                steps.append(_step("hacker", T["hit"].format(i=i) + _fmt_result(r.status_code, d, lang)))
                found = True
                break
        if not found:
            steps.append(_step("hacker", T["miss"]))
        steps.append(_step("system", T["end"]))
    reset_demo_counters()
    return steps


async def attack_brute(lang: str = "mn") -> list[dict]:
    T = {
        "mn": dict(try_line="admin / {pw} → HTTP {code} (хаалттай)",
                   end="Буруу нууц үг бүр 401 Unauthorized. Админ функц нууц үггүйгээр ажиллахгүй."),
        "ko": dict(try_line="admin / {pw} → HTTP {code} (차단됨)",
                   end="잘못된 비밀번호마다 401 Unauthorized. 관리자 기능은 비밀번호 없이는 작동하지 않습니다."),
    }[lang]
    steps = []
    async with httpx.AsyncClient(timeout=10) as client:
        for pw in ("123456", "password", "admin", "qwerty", "letmein"):
            r = await client.request("DELETE", f"{API}/admin/revoke/test", auth=("admin", pw))
            steps.append(_step("hacker", T["try_line"].format(pw=pw, code=r.status_code)))
        steps.append(_step("system", T["end"]))
    return steps


async def attack_flood(lang: str = "mn") -> list[dict]:
    T = {
        "mn": dict(start="220 хүсэлт илгээж байна...",
                   result="Хүлээн авсан: {ok}   Хаасан (429): {blocked}",
                   end="Нэг IP-ээс минутад 200-аас их хүсэлт ирвэл Rate Limit хаана. Сервер унаагүй, ажилласаар байна.",
                   cleaned="(Демогийн дараа тоолуурыг цэвэрлэлээ — дашбоард хэвийн ажиллана.)"),
        "ko": dict(start="220개의 요청을 전송 중...",
                   result="수신됨: {ok}   차단됨 (429): {blocked}",
                   end="한 IP에서 분당 200개를 초과하면 Rate Limit이 차단합니다. 서버는 다운되지 않고 계속 작동합니다.",
                   cleaned="(데모 후 카운터를 초기화했습니다 — 대시보드가 정상 작동합니다.)"),
    }[lang]
    steps = []
    reset_demo_counters()
    steps.append(_step("hacker", T["start"]))
    ok = 0
    blocked = 0
    async with httpx.AsyncClient(timeout=10) as client:
        async def one():
            nonlocal ok, blocked
            try:
                r = await client.post(f"{API}/validate", json={"token": "x"})
                if r.status_code == 429:
                    blocked += 1
                else:
                    ok += 1
            except Exception:
                pass

        batch = 20
        for i in range(0, 220, batch):
            await asyncio.gather(*[one() for _ in range(min(batch, 220 - i))])

    steps.append(_step("system", T["result"].format(ok=ok, blocked=blocked)))
    steps.append(_step("system", T["end"]))
    reset_demo_counters()
    steps.append(_step("system", T["cleaned"]))
    return steps


ATTACKS = {
    "stolen": attack_stolen,
    "forge": attack_forge,
    "replay": attack_replay,
    "scan": attack_scan,
    "brute": attack_brute,
    "flood": attack_flood,
}
