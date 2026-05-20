# 🚀 ЭХЛЭХ ЗААВАР — Алхам алхмаар

## 📁 1-р алхам: Фолдер бэлдэх

1. `zero_persistence` фолдерийг ширээний компьютер дээрх дурын газарт хадгал
2. VS Code нээ → File → Open Folder → `zero_persistence` фолдерийг сонго

---

## 💻 2-р алхам: Terminal нээх (VS Code-д)

VS Code дотор: **Terminal → New Terminal** (эсвэл Ctrl + `)

---

## 🔧 3-р алхам: Virtual Environment үүсгэх

Terminal дотор дараах командыг хуулж тавь:

```
python -m venv venv
```

Дараа нь идэвхжүүл (Windows):
```
venv\Scripts\activate
```

✅ Амжилттай бол terminal-д `(venv)` гарна.

---

## 📦 4-р алхам: Шаардлагатай сангуудыг суулгах

```
pip install -r requirements.txt
```

⏳ 2-3 минут хүлээнэ.

---

## 🐳 5-р алхам: Redis эхлүүлэх

Docker Desktop-ийг нээгээд ажиллаж байгаа эсэхийг шалга.
Дараа нь terminal дотор:

```
docker run -d --name my-redis -p 6379:6379 redis:alpine redis-server --save "" --appendonly no
```

✅ Redis ажиллаж байгааг шалгах:
```
docker ps
```
`my-redis` гарч ирвэл зөв.

---

## ▶️ 6-р алхам: API серверийг эхлүүлэх

```
uvicorn main:app --reload
```

✅ Дараах зүйл гарч ирвэл амжилттай:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
✅ Scheduler эхэлсэн
```

---

## 🌐 7-р алхам: API туршиж үзэх

Браузер дээр нээ: **http://localhost:8000/docs**

Тэнд бүх endpoint-ийн жагсаалт гарч ирнэ. Дарж шууд туршиж болно.

### Гараар туршиx (Postman эсвэл curl):

**Токен авах:**
```
POST http://localhost:8000/request-token
Body (JSON): {"user_id": "alice", "max_uses": 10}
```

**Токен шалгах:**
```
POST http://localhost:8000/validate
Body (JSON): {"token": "энд авсан токеноо тавь"}
```

**Admin токен устгах:**
```
DELETE http://localhost:8000/admin/revoke/{jti}
Basic Auth: admin / admin123
```

---

## 🧪 8-р алхам: Тест ажиллуулах

Шинэ terminal нээгээд (Redis болон uvicorn ажиллаж байх ёстой):

```
pytest test_system.py -v
```

Coverage тайлан (HTML):
```
pytest test_system.py -v --cov=. --cov-report=html
```
Дараа нь `htmlcov/index.html` файлыг браузерт нээ.

---

## 📊 9-р алхам: Grafana Dashboard (заавал биш, нэмэлт)

```
docker-compose up -d
```

Дараа нь нээ: **http://localhost:3000** (нэвтрэлт: admin / admin)

---

## 📈 10-р алхам: Ачааны тест (Locust)

```
locust -f locustfile.py --host=http://localhost:8000
```

Нээ: **http://localhost:8089**
- Number of users: 1000
- Spawn rate: 10
- Дараа нь Start → Хэмжилтийг хар

---

## ❌ Нийтлэг алдаа ба шийдэл

| Алдаа | Шийдэл |
|-------|--------|
| `redis.exceptions.ConnectionError` | Docker дээр Redis ажиллаж байгаа эсэхийг шалга |
| `ModuleNotFoundError` | `pip install -r requirements.txt` дахин ажиллуул |
| `(venv)` гарахгүй байна | `venv\Scripts\activate` буруу замд байна |
| Port 8000 already in use | `uvicorn main:app --reload --port 8001` |

---

## 📝 Дипломын ажилд шаардлагатай screenshots

1. `/docs` хуудас
2. Postman-аас токен авах → баталгаажуулах
3. `pytest -v` тестийн үр дүн
4. `--cov-report=html` coverage хувь
5. Locust график (1000 хэрэглэгч)
6. Grafana dashboard
7. `destruct_events.log` файл (автомат устгалтын бичлэг)
