# 🍎 Mac дээр ажиллуулах заавар (эхнээс нь, алхам алхмаар)

> Энэ заавар зөвхөн **Mac**-д зориулсан. Команд бүрийг **хуулж аваад Terminal-д тавиад Enter** дарна. Өөр юм бодох хэрэггүй.

---

## 0. Ойлгох хэрэгтэй 4 үг

| Үг | Энгийнээр |
|----|-----------|
| **Terminal** | Команд бичдэг хар цонх |
| **Docker** | Програмуудыг "хайрцаг" (container) дотор асаадаг програм. Redis, Grafana-г бид суулгахгүй, Docker татаж аваад асаана |
| **Redis** | Токенуудыг санах ойд хадгалдаг өгөгдлийн сан (диск рүү бичдэггүй) |
| **venv** | Энэ төслийн Python сангууд тусдаа суудаг фолдер |

---

## 1. Terminal нээх

`Cmd + Space` → **Terminal** гэж бичнэ → Enter.

## 2. Төслийн фолдер руу орох

```bash
cd ~/Downloads/capstone_geroooo/lets_gero/lets_gero
```

Зөв орсон эсэхээ шалгах:
```bash
ls
```
`main.py`, `docker-compose.yml` гэх мэт файлууд харагдвал зөв байна.

> 💡 **Шинэ Terminal цонх нээх бүрт** энэ `cd ...` командыг дахин ажиллуулна.

## 3. Docker Desktop асаах

1. Finder → Applications → **Docker**-ийг давхар дарна
2. Дээд мөрөнд 🐳 халим гарч ирээд хөдлөхөө болих хүртэл (~30 сек) хүлээнэ
3. Шалгах:
```bash
docker info
```
`Server Version: ...` гэсэн мөр гарвал Docker ажиллаж байна.
`Cannot connect to the Docker daemon` гэж гарвал Docker Desktop хараахан асаагүй байна, жаахан хүлээгээд дахин оролдоно.

## 4. Хуучин Redis контейнерийг устгах (ганц удаа)

Өмнө нь `docker run ... my-redis` ажиллуулж байсан бол 6379 порт давхцана. Устгана:
```bash
docker rm -f my-redis
```
`No such container` гэж гарвал байхгүй байсан гэсэн үг, зүгээр.

---

## 5. 🐳 БҮГДИЙГ НЭГ КОМАНДААР АСААХ (хамгийн амар)

```bash
docker compose up -d --build
```

Анх удаа 2-5 минут болно (зургуудыг интернэтээс татна). Дараа нь шалгах:
```bash
docker compose ps
```
Дараах 5 мөр **Up** / **running** гэж харагдах ёстой:

| Контейнер | Юу хийдэг | Хаяг |
|-----------|-----------|------|
| `zero-redis` | Токен хадгална | — |
| `zero-api` | Таны FastAPI сервер | http://localhost:8000 |
| `zero-redis-exporter` | Redis-ийн тоо баримтыг гаргана | http://localhost:9121/metrics |
| `zero-prometheus` | Тоо баримтыг 5 сек бүр цуглуулна | http://localhost:9090 |
| `zero-grafana` | График dashboard | http://localhost:3000 |

### Браузер дээр нээх

- **Dashboard:** http://localhost:8000
- **API туршилт (Swagger):** http://localhost:8000/docs
- **Grafana:** http://localhost:3000 → нэвтрэх `admin` / `admin` → "Skip" дарна → зүүн цэс **Dashboards** → **Zero-Persistence Token System**
- **Prometheus шалгах:** http://localhost:9090/targets → `redis` нь **UP** (ногоон) байх ёстой

> Grafana хоосон харагдвал: 1-2 минут хүлээ, мөн /docs дээр хэдэн токен аваад үз. Тэгвэл "Идэвхтэй токен" өсөх ёстой.

### Логийг харах (алдаа гарвал)
```bash
docker compose logs -f api
```
Гарахдаа `Ctrl + C`.

### Унтраах
```bash
docker compose down
```

---

## 6. 🧪 Тест ба Locust ажиллуулах (Python хэрэгтэй)

Тест болон Locust нь Mac дээр шууд Python-оор ажилладаг. **5-р алхмын контейнерууд асаалттай байх ёстой** (Redis хэрэгтэй).

### 6.1 Python 3.11 байгаа эсэх
```bash
python3.11 --version
```
`Python 3.11.x` гарвал зөв. `command not found` гарвал:
```bash
brew install python@3.11
```

### 6.2 Windows-ийн хуучин venv-ийг устгаад шинээр үүсгэх (ганц удаа)
Zip дотор ирсэн `venv` нь Windows-ийнх тул Mac дээр ажиллахгүй.
```bash
rm -rf venv
```
```bash
python3.11 -m venv venv
```

### 6.3 venv идэвхжүүлэх (шинэ Terminal нээх бүрт)
```bash
source venv/bin/activate
```
Мөрийн эхэнд `(venv)` гарч ирнэ.

### 6.4 Сангууд суулгах (ганц удаа, 2-3 минут)
```bash
pip install -r requirements.txt
```

### 6.5 Тест
```bash
pytest test_system.py -v --cov=. --cov-report=html
```
Coverage тайланг нээх:
```bash
open htmlcov/index.html
```

### 6.6 Locust (ачааны тест)
```bash
locust -f locustfile.py --host=http://localhost:8000
```
Браузерт http://localhost:8089 → Users: `1000`, Spawn rate: `10` → **Start**.
Энэ үед Grafana-г зэрэг нээвэл графикууд хөдөлж байгааг харна. Үүнийг screenshot авахад тохиромжтой.
Зогсоохдоо Terminal дээр `Ctrl + C`.

---

## 7. (Нэмэлт) Серверийг Docker-гүйгээр, `--reload`-той ажиллуулах

Код засаад шууд харахыг хүсвэл. **Docker-ийн `zero-api`-г зогсоох хэрэгтэй**, эс бөгөөс 8000 порт давхцана:
```bash
docker compose stop api
```
```bash
uvicorn main:app --reload
```
Буцаагаад Docker-ийн API-г асаах:
```bash
docker compose start api
```

---

## ❌ Түгээмэл алдаа

| Алдаа | Шийдэл |
|-------|--------|
| `Cannot connect to the Docker daemon` | Docker Desktop асаагүй байна → 3-р алхам |
| `port is already allocated` (6379) | `docker rm -f my-redis` |
| `address already in use` (8000) | `docker compose stop api` эсвэл өөр Terminal-д uvicorn ажиллаж байна, тэр Terminal-д `Ctrl + C` |
| `redis.exceptions.ConnectionError` (тест дээр) | `docker compose up -d redis`. Мөн `.env` дотор `REDIS_HOST=localhost` байх ёстой (`redis` биш — Docker доторх API-д compose өөрөө `redis` гэж тохируулдаг) |
| `ModuleNotFoundError` | `source venv/bin/activate` хийгээгүй байна |
| `zsh: command not found: python3.11` | `brew install python@3.11` |
| `context_drift_detected` нэг минутын дараа | Кодын мэдэгдэж буй алдаа (context.py дахь минутын цонх). Шинэ токен аваад шууд шалга |

---

## 📸 Дипломд хэрэгтэй screenshot-ууд

1. `docker compose ps` — 5 контейнер ажиллаж байгаа
2. http://localhost:8000/docs
3. Токен авах → `/validate` хийх
4. `pytest -v` үр дүн + `htmlcov` coverage
5. Locust график (1000 хэрэглэгч)
6. Grafana dashboard (Locust ажиллаж байх үед)
7. Prometheus targets хуудас (UP)
8. `destruct_events.log` файл
