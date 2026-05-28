Zero-Persistence Self-Destructing Token System
API tokens that automatically invalidate within seconds of a credential leak — zero disk persistence, maximum security.

Tests Coverage Python Docker Security

What is this?
A cybersecurity system that automatically destroys API tokens within seconds of a credential leak. Unlike traditional JWT systems, tokens are never written to disk and self-destruct under 5 different conditions.

Quick Start
Option 1 — Docker (Recommended)

git clone https://github.com/mBlYaTm/capstone_gerooo2
cd capstone_gerooo2
docker-compose up -d
Option 2 — Manual

# Install dependencies
pip install -r requirements.txt

# Start Redis
docker run -d --name my-redis -p 6379:6379 redis:alpine redis-server --save "" --appendonly no

# Start server
py -m uvicorn main:app --reload
Open dashboard → http://localhost:8000

Features
Zero-Persistence — tokens never saved to disk, memory only
Context Binding — tokens locked to IP address and User-Agent
4 Anomaly Detectors — real-time attack detection with risk scoring
5 Auto-Destruct Triggers — automatic token deletion on threat detection
Telegram Alerts — instant HIGH risk notifications to your phone
Live Dashboard — real-time event feed, dark and light mode
Security Headers — CSP, X-Frame-Options, X-XSS-Protection
Rate Limiting — 200 requests per minute per IP
SSE Real-time — dashboard updates without page refresh
How It Works
6-Step Token Validation Pipeline
Request comes in
       │
       ▼
Step 1 — JWT signature check
       │
       ▼
Step 2 — Redis existence check (TTL auto-expiry)
       │
       ▼
Step 3 — Context binding (IP + User-Agent match)
       │
       ▼
Step 4 — Max uses check
       │
       ▼
Step 5 — Anomaly risk score check
       │
       ▼
Step 6 — Increment use counter → return valid
4 Anomaly Detectors
Detector	Trigger	Risk Score
Replay Attack	Same JTI used twice	+30
Velocity Burst	10+ requests per second	+40
Geo Impossible	Physically impossible travel	+50
Endpoint Enum	5+ 404 path probing	+35
Risk Levels

LOW (0–30) → Allow request
MEDIUM (31–60) → Log and allow
HIGH (61+) → Destroy token + Telegram alert
5 Auto-Destruct Triggers
#	Trigger	How
1	TTL Expiry	Redis auto-delete after 300s
2	Context Drift	IP address changed
3	Max Uses	Usage limit exceeded
4	High Risk	Anomaly score ≥ 61
5	Admin Revoke	Manual deletion via API

Test Results
pytest test_system.py -v --cov=. --cov-report=html

41 passed in 2.87s ✅
Coverage: 81% ✅
File	Coverage
context.py	100%
crypto_utils.py	100%
token_engine.py	92%
main.py	85%
redis_store.py	81%
destruct_engine.py	78%
Project Structure
zero_persistence/
│
├── main.py                 FastAPI entry point + SSE + Security Headers + Rate Limiting
├── token_engine.py         Token creation and 6-step validation + Telegram alerts
├── redis_store.py          Redis operations — store, delete, check tokens
├── context.py              IP and User-Agent binding
├── detectors.py            4 anomaly detectors and RiskScorer class
├── destruct_engine.py      5 auto-destruct triggers and event logging
├── alerting.py             Telegram security alert system
├── crypto_utils.py         SHA-256 token hashing
├── dashboard.html          Live security dashboard
│
├── test_system.py          41 unit tests
├── load_test.py            Load testing — 20 concurrent users
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                    Secret config — never committed to GitHub

Tech Stack
Technology	Purpose
FastAPI	REST API framework + SSE
Redis	Zero-persistence in-memory token storage
Docker	Containerization
JWT HS256	Token signing and verification
SHA-256	Secure token hashing
APScheduler	Background cleanup every 60 seconds
Telegram Bot API	Real-time security alerts
pytest	Unit testing framework
httpx	HTTP client for Telegram
📱 Telegram Alert Example
When HIGH risk is detected, an instant alert is sent:

 SECURITY ALERT!
━━━━━━━━━━━━━━━━━
Event: Anomaly HIGH Risk
IP: 127.0.0.1
Risk Score: 70 (HIGH)
Reasons: replay_attack, velocity_burst
Action: Token destroyed
Time: 2026-05-28 09:52:52
JTI: b54de84a...


 Security Headers
All API responses include these security headers:

Content-Security-Policy
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000
X-RateLimit-Limit: 200
X-RateLimit-Remaining: [count]


Docker Services
services:
  redis     → port 6379   Zero-persistence token storage
  api       → port 8000   FastAPI server
  grafana   → port 3000   Monitoring dashboard


Capstone Project
Department: Cybersecurity Engineering Year: 2026 GitHub: https://github.com/mBlYaTm/capstone_gerooo2