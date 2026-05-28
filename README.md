# 🛡️ Zero-Persistence Self-Destructing Token System

> API tokens that automatically invalidate within seconds of a credential leak

![Tests](https://img.shields.io/badge/tests-41%2F41-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-81%25-blue)
![Python](https://img.shields.io/badge/python-3.13-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)

---

## 🔥 What is this?

A cybersecurity system that automatically destroys API tokens within seconds of a credential leak. Tokens are never written to disk and self-destruct under 5 different conditions.

---

## 🚀 Quick Start

**Docker (Recommended)**

```bash
git clone https://github.com/mBlYaTm/capstone_gerooo2
cd capstone_gerooo2
docker-compose up -d
```

**Manual**

```bash
pip install -r requirements.txt
docker run -d --name my-redis -p 6379:6379 redis:alpine
py -m uvicorn main:app --reload
```

Open → **http://localhost:8000**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔒 Zero-Persistence | Tokens never saved to disk |
| 🔗 Context Binding | Tokens locked to IP + User-Agent |
| 🚨 4 Anomaly Detectors | Real-time attack detection |
| 💥 5 Auto-Destruct Triggers | Automatic token deletion |
| 📱 Telegram Alerts | Instant HIGH risk notifications |
| 📊 Live Dashboard | Dark/light mode, real-time feed |
| 🛡️ Security Headers | CSP, X-Frame-Options, Rate Limiting |

---

## 🔐 4 Anomaly Detectors

| Detector | Trigger | Score |
|---|---|---|
| Replay Attack | Same JTI used twice | +30 |
| Velocity Burst | 10+ requests per second | +40 |
| Geo Impossible | Physically impossible travel | +50 |
| Endpoint Enum | 5+ 404 path probing | +35 |

- **LOW (0–30)** → Allow
- **MEDIUM (31–60)** → Log
- **HIGH (61+)** → Destroy token + Telegram alert

---

## 💥 5 Auto-Destruct Triggers

| # | Trigger | Condition |
|---|---|---|
| 1 | TTL Expiry | Redis auto-delete after 300s |
| 2 | Context Drift | IP address changed |
| 3 | Max Uses | Usage limit exceeded |
| 4 | High Risk | Anomaly score ≥ 61 |
| 5 | Admin Revoke | Manual deletion via API |

---

## 📊 Test Results

- ✅ 41/41 tests PASSED
- ✅ Coverage: 81%
- ✅ OWASP ZAP: 0 critical vulnerabilities

---

## 📁 Project Structure


zero_persistence/ 
├── main.py FastAPI + SSE + Security Headers + Rate Limiting 
├── token_engine.py Token creation + 6-step validation + Telegram 
├── redis_store.py Redis operations 
├── context.py IP + User-Agent binding 
├── detectors.py 4 anomaly detectors + RiskScorer 
├── destruct_engine.py 5 auto-destruct triggers 
├── alerting.py Telegram alerts 
├── crypto_utils.py SHA-256 hashing 
├── dashboard.html Live dashboard 
├── test_system.py 41 unit tests 
├── load_test.py Load testing 
├── Dockerfile └── docker-compose.yml  




## 🔧 Tech Stack

| Technology | Purpose |
|---|---|
| FastAPI | REST API + SSE |
| Redis | Zero-persistence storage |
| Docker | Containerization |
| JWT HS256 | Token signing |
| SHA-256 | Token hashing |
| APScheduler | Background cleanup |
| Telegram Bot | Real-time alerts |
| pytest | Unit testing |
