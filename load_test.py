# load_test.py - Simple load test
import threading
import time
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
NUM_USERS = 20
REQUESTS_PER_USER = 10
results = []

def user_session(user_id: int):
    session_results = {"success": 0, "failed": 0, "times": []}
    try:
        # Issue token
        start = time.time()
        r = httpx.post(f"{BASE_URL}/request-token",
                       json={"user_id": f"load_user_{user_id}", "max_uses": 50},
                       timeout=10)
        elapsed = (time.time() - start) * 1000

        if r.status_code != 200:
            session_results["failed"] += 1
            return session_results

        token = r.json().get("token", "")
        session_results["success"] += 1
        session_results["times"].append(elapsed)

        # Validate IMMEDIATELY many times — no sleep — triggers velocity burst
        for _ in range(REQUESTS_PER_USER - 1):
            start = time.time()
            rv = httpx.post(f"{BASE_URL}/validate",
                            json={"token": token},
                            timeout=10)
            elapsed = (time.time() - start) * 1000
            session_results["times"].append(elapsed)
            if rv.status_code == 200:
                session_results["success"] += 1
            else:
                session_results["failed"] += 1

    except Exception as e:
        session_results["failed"] += 1
    return session_results


def run_load_test():
    print(f"\n{'='*55}")
    print(f"  ZERO-PERSISTENCE TOKEN SYSTEM — LOAD TEST")
    print(f"{'='*55}")
    print(f"  Users:             {NUM_USERS}")
    print(f"  Requests per user: {REQUESTS_PER_USER}")
    print(f"  Total requests:    {NUM_USERS * REQUESTS_PER_USER}")
    print(f"{'='*55}\n")

    try:
        h = httpx.get(f"{BASE_URL}/health", timeout=5)
        print(f"  Server status: {h.json().get('status','unknown').upper()}")
    except:
        print("  ERROR: Server is not running!")
        return

    print(f"\n  Starting {NUM_USERS} concurrent users...\n")
    start_time = time.time()

    threads = []
    thread_results = [None] * NUM_USERS

    def run_user(uid):
        thread_results[uid] = user_session(uid)

    for i in range(NUM_USERS):
        t = threading.Thread(target=run_user, args=(i,))
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    total_time = time.time() - start_time

    all_times = []
    total_success = 0
    total_failed = 0

    for r in thread_results:
        if r:
            total_success += r["success"]
            total_failed += r["failed"]
            all_times.extend(r["times"])

    all_times.sort()
    total_requests = total_success + total_failed
    avg_ms    = sum(all_times) / len(all_times) if all_times else 0
    p99_ms    = all_times[int(len(all_times) * 0.99)] if all_times else 0
    rps       = total_requests / total_time if total_time > 0 else 0
    pass_rate = (total_success / total_requests * 100) if total_requests > 0 else 0

    print(f"{'='*55}")
    print(f"  RESULTS")
    print(f"{'='*55}")
    print(f"  Total requests:    {total_requests}")
    print(f"  Successful:        {total_success} ({pass_rate:.1f}%)")
    print(f"  Failed:            {total_failed}")
    print(f"  Requests/sec:      {rps:.1f}")
    print(f"  Average:           {avg_ms:.1f}ms")
    print(f"  99th percentile:   {p99_ms:.1f}ms")
    print(f"{'='*55}\n")

    report = {
        "timestamp": datetime.now().isoformat(),
        "results": {
            "total_requests": total_requests,
            "successful": total_success,
            "failed": total_failed,
            "pass_rate_percent": round(pass_rate, 1),
            "requests_per_second": round(rps, 1),
        }
    }
    with open("load_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Report saved: load_test_report.json\n")

if __name__ == "__main__":
    run_load_test()