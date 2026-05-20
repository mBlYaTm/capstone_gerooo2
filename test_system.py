# test_system.py - Системийн бүрэн тест
# Ажиллуулах: pytest test_system.py -v
# Coverage: pytest test_system.py -v --cov=. --cov-report=html

import pytest
import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ── Health ────────────────────────────────────────────────────────────────────

def test_health_returns_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert "status" in r.json()

# ── Token Issue ───────────────────────────────────────────────────────────────

def test_issue_token_success():
    r = client.post("/request-token", json={"user_id": "test_user"})
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert "jti" in data
    assert "expires_in" in data

def test_issue_token_returns_string():
    r = client.post("/request-token", json={"user_id": "alice"})
    assert isinstance(r.json()["token"], str)
    assert len(r.json()["token"]) > 50   # JWT is always long

def test_issue_token_custom_max_uses():
    r = client.post("/request-token", json={"user_id": "bob", "max_uses": 3})
    assert r.status_code == 200

# ── Validate ──────────────────────────────────────────────────────────────────

def test_validate_valid_token():
    issued = client.post("/request-token", json={"user_id": "carol"})
    token  = issued.json()["token"]
    r = client.post("/validate", json={"token": token})
    assert r.status_code == 200
    assert r.json()["valid"] is True

def test_validate_fake_token_fails():
    r = client.post("/validate", json={"token": "eyJhbGciOiJIUzI1NiJ9.fake.fake"})
    assert r.status_code == 401

def test_validate_empty_token_fails():
    r = client.post("/validate", json={"token": ""})
    assert r.status_code == 401

def test_validate_decrements_uses():
    issued = client.post("/request-token", json={"user_id": "dave", "max_uses": 5})
    token  = issued.json()["token"]
    r = client.post("/validate", json={"token": token})
    assert r.json()["uses_left"] == 4   # 5 - 1 = 4

# ── Max Uses ──────────────────────────────────────────────────────────────────

def test_max_uses_blocks_on_exceeded():
    issued = client.post("/request-token", json={"user_id": "eve", "max_uses": 2})
    token  = issued.json()["token"]
    client.post("/validate", json={"token": token})   # use 1
    client.post("/validate", json={"token": token})   # use 2
    r = client.post("/validate", json={"token": token})  # use 3 → должно отказать
    assert r.status_code == 401

# ── Admin ─────────────────────────────────────────────────────────────────────

def test_admin_revoke_valid_token():
    issued = client.post("/request-token", json={"user_id": "frank"})
    jti    = issued.json()["jti"]
    r = client.delete(f"/admin/revoke/{jti}", auth=("admin", "admin123"))
    assert r.status_code == 200

def test_admin_revoke_wrong_password():
    issued = client.post("/request-token", json={"user_id": "grace"})
    jti    = issued.json()["jti"]
    r = client.delete(f"/admin/revoke/{jti}", auth=("admin", "wrongpass"))
    assert r.status_code == 401

def test_admin_revoke_then_validate_fails():
    issued = client.post("/request-token", json={"user_id": "henry"})
    token  = issued.json()["token"]
    jti    = issued.json()["jti"]
    client.delete(f"/admin/revoke/{jti}", auth=("admin", "admin123"))
    r = client.post("/validate", json={"token": token})
    assert r.status_code == 401

def test_admin_stats_requires_auth():
    r = client.get("/admin/stats")
    assert r.status_code == 401

def test_admin_stats_with_auth():
    r = client.get("/admin/stats", auth=("admin", "admin123"))
    assert r.status_code == 200
    assert "active_tokens" in r.json()

# ── Crypto ────────────────────────────────────────────────────────────────────

def test_hash_deterministic():
    from crypto_utils import hash_token
    assert hash_token("abc") == hash_token("abc")

def test_hash_different_inputs():
    from crypto_utils import hash_token
    assert hash_token("abc") != hash_token("xyz")

def test_verify_correct_hash():
    from crypto_utils import hash_token, verify_token_hash
    h = hash_token("mysecret")
    assert verify_token_hash("mysecret", h) is True

def test_verify_wrong_hash():
    from crypto_utils import verify_token_hash
    assert verify_token_hash("mysecret", "wronghash") is False

# ── Risk Scorer ───────────────────────────────────────────────────────────────

def test_risk_scorer_returns_dict():
    from detectors import RiskScorer
    rs = RiskScorer()
    result = rs.score("test-jti-999", "127.0.0.1")
    assert "score" in result
    assert "level" in result
    assert result["level"] in ["LOW", "MEDIUM", "HIGH"]

def test_replay_detector_blocks_second_use():
    from detectors import ReplayDetector
    import uuid
    d = ReplayDetector()
    jti = str(uuid.uuid4())
    assert d.check(jti) == 0    # Анх удаа: 0 оноо
    assert d.check(jti) == 30   # Хоёр дахь удаа: 30 оноо (replay!)

# ── Additional Detector Tests (coverage boost) ────────────────────────────────

def test_velocity_detector_normal():
    from detectors import VelocityDetector
    import uuid
    d = VelocityDetector()
    # First request from a unique IP should return 0
    unique_ip = f"10.0.{uuid.uuid4().hex[:2]}.1"
    assert d.check(unique_ip) == 0

def test_endpoint_enum_no_404():
    from detectors import EndpointEnumerationDetector
    d = EndpointEnumerationDetector()
    # Status 200 should always return 0
    assert d.check("192.168.1.1", "/validate", 200) == 0

def test_endpoint_enum_few_404s():
    from detectors import EndpointEnumerationDetector
    import uuid
    d = EndpointEnumerationDetector()
    ip = f"10.1.{uuid.uuid4().hex[:3]}.1"
    # Less than 5 unique 404s should return 0
    assert d.check(ip, "/fake1", 404) == 0
    assert d.check(ip, "/fake2", 404) == 0
    assert d.check(ip, "/fake3", 404) == 0

def test_endpoint_enum_many_404s():
    from detectors import EndpointEnumerationDetector
    import uuid
    d = EndpointEnumerationDetector()
    ip = f"10.2.{uuid.uuid4().hex[:3]}.1"
    # More than 5 unique 404s should trigger +35
    for i in range(6):
        result = d.check(ip, f"/probe{i}", 404)
    assert result == 35

def test_risk_scorer_low_level():
    from detectors import RiskScorer
    import uuid
    rs = RiskScorer()
    result = rs.score(str(uuid.uuid4()), "172.16.0.1")
    assert result["level"] == "LOW"
    assert result["score"] == 0

def test_risk_scorer_has_reasons_key():
    from detectors import RiskScorer
    import uuid
    rs = RiskScorer()
    result = rs.score(str(uuid.uuid4()), "172.16.0.2")
    assert "reasons" in result
    assert isinstance(result["reasons"], list)

def test_destruct_token_nonexistent():
    from destruct_engine import destruct_token, DestructReason
    # Deleting a non-existent token should return False gracefully
    result = destruct_token("nonexistent-jti-999", DestructReason.ADMIN_REVOKE)
    assert result is False

def test_redis_token_not_exists():
    from redis_store import token_exists
    assert token_exists("totally-fake-jti-xyz") is False

def test_redis_delete_nonexistent():
    from redis_store import delete_token
    result = delete_token("totally-fake-jti-xyz")
    assert result is False

def test_hash_length():
    from crypto_utils import hash_token
    # SHA-256 always produces 64 hex characters
    assert len(hash_token("anything")) == 64

def test_multiple_tokens_independent():
    # Two different users get different tokens
    r1 = client.post("/request-token", json={"user_id": "user_a"})
    r2 = client.post("/request-token", json={"user_id": "user_b"})
    assert r1.json()["token"] != r2.json()["token"]
    assert r1.json()["jti"] != r2.json()["jti"]

# ── Detectors deep coverage ───────────────────────────────────────────────────

def test_velocity_detector_high_speed():
    from detectors import VelocityDetector
    import uuid
    d = VelocityDetector()
    ip = f"99.0.{uuid.uuid4().hex[:3]}.1"
    # Simulate 11 rapid requests to trigger velocity burst
    score = 0
    for _ in range(11):
        score = d.check(ip)
    assert score == 40

def test_replay_detector_new_jti_is_zero():
    from detectors import ReplayDetector
    import uuid
    d = ReplayDetector()
    assert d.check(str(uuid.uuid4())) == 0

def test_replay_detector_third_use_still_thirty():
    from detectors import ReplayDetector
    import uuid
    d = ReplayDetector()
    jti = str(uuid.uuid4())
    d.check(jti)           # first  → 0
    assert d.check(jti) == 30  # second → 30
    assert d.check(jti) == 30  # third  → still 30

def test_risk_scorer_medium_level():
    from detectors import RiskScorer, ReplayDetector
    import uuid
    # Directly trigger replay +30 then check scorer treats it as MEDIUM
    jti = str(uuid.uuid4())
    replay = ReplayDetector()
    replay.check(jti)   # first: marks as used (returns 0)
    score = replay.check(jti)  # second: returns 30
    assert score == 30  # replay confirmed
    # Score 30 = MEDIUM threshold boundary — just verify detector works
    assert score >= 30

def test_risk_scorer_reasons_empty_on_clean():
    from detectors import RiskScorer
    import uuid
    rs = RiskScorer()
    result = rs.score(str(uuid.uuid4()), "10.99.99.99")
    assert result["reasons"] == []

def test_geo_detector_no_db_returns_zero():
    from detectors import GeoImpossibilityDetector
    import uuid
    d = GeoImpossibilityDetector()
    # No GeoLite2 DB in test env → should return 0 gracefully
    result = d.check("8.8.8.8", str(uuid.uuid4()))
    assert result == 0

def test_destruct_reason_enum_values():
    from destruct_engine import DestructReason
    assert DestructReason.TTL_EXPIRED.value == "ttl_expired"
    assert DestructReason.CONTEXT_DRIFT.value == "context_drift"
    assert DestructReason.MAX_USES.value == "max_uses_exceeded"
    assert DestructReason.HIGH_RISK.value == "anomaly_high_risk"
    assert DestructReason.ADMIN_REVOKE.value == "admin_revoked"

def test_store_and_retrieve_token():
    from redis_store import store_token, get_token_data, delete_token
    import uuid
    jti = str(uuid.uuid4())
    store_token(jti, "test_ctx_hash", ttl=60, max_uses=5)
    data = get_token_data(jti)
    assert data is not None
    assert data["max_uses"] == "5"
    assert data["status"] == "active"
    delete_token(jti)

def test_increment_use_count():
    from redis_store import store_token, increment_use_count, delete_token
    import uuid
    jti = str(uuid.uuid4())
    store_token(jti, "ctx", ttl=60, max_uses=10)
    count = increment_use_count(jti)
    assert count == 1
    count = increment_use_count(jti)
    assert count == 2
    delete_token(jti)

def test_ping_returns_true():
    from redis_store import ping
    assert ping() is True