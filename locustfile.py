# locustfile.py - 1000 хэрэглэгчийн ачааны тест
# Суулгах: pip install locust
# Ажиллуулах: locust -f locustfile.py --host=http://localhost:8000
# Дараа нь: http://localhost:8089 нээнэ

from locust import HttpUser, task, between


class TokenUser(HttpUser):
    wait_time = between(0.1, 0.5)   # 0.1-0.5 секунд хүлээнэ

    def on_start(self):
        """Хэрэглэгч бүр эхлэхэд нэг токен авна"""
        resp = self.client.post("/request-token", json={
            "user_id": f"load_test_user_{self.environment.runner.user_count}",
            "max_uses": 1000
        })
        if resp.status_code == 200:
            self.token = resp.json().get("token", "")
        else:
            self.token = ""

    @task(3)
    def validate_token(self):
        """Токен баталгаажуулах (3 дахин илүү хийнэ)"""
        if self.token:
            self.client.post("/validate", json={"token": self.token})

    @task(1)
    def issue_new_token(self):
        """Шинэ токен авах"""
        resp = self.client.post("/request-token", json={
            "user_id": "perf_test",
            "max_uses": 100
        })
        if resp.status_code == 200:
            self.token = resp.json().get("token", "")

    @task(1)
    def health_check(self):
        """Health endpoint шалгах"""
        self.client.get("/health")
