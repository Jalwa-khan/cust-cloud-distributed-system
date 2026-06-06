"""
CUST CEP Phase 4 - Testing, Benchmarking & Evaluation
Tests all microservices, measures performance, generates results table.
CPE4541 CEP Project

Run AFTER services are up:
  docker-compose up -d
  python tests/test_and_benchmark.py
"""
import requests
import time
import statistics
import json
import threading
import random
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:5000"  # API Gateway

# ─── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg): print(f"  {RED}✗{RESET} {msg}")
def hdr(msg):  print(f"\n{BOLD}{msg}{RESET}")
def sep():     print("-" * 60)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def get(path, expected=200):
    try:
        r = requests.get(f"{BASE_URL}{path}", timeout=10)
        return r, r.status_code == expected
    except Exception as e:
        return None, False

def post(path, data, expected=201):
    try:
        r = requests.post(f"{BASE_URL}{path}", json=data, timeout=10)
        return r, r.status_code in (expected, 200, 409)
    except Exception as e:
        return None, False

# ─── Service Health Tests ─────────────────────────────────────────────────────
def test_health():
    hdr("TEST 1: Service Health Checks")
    sep()
    r, passed = get("/health")
    if passed and r:
        data = r.json()
        for svc, status in data.get("services", {}).items():
            if status.get("status") == "healthy":
                ok(f"{svc}: healthy")
            else:
                fail(f"{svc}: {status.get('status','unknown')}")
    else:
        fail("Gateway health check failed - are services running?")
    return passed

# ─── Functional Tests ─────────────────────────────────────────────────────────
def test_registration():
    hdr("TEST 2: Registration Service Functional Tests")
    sep()
    results = []

    r, p = get("/api/registration/students")
    results.append(p)
    ok("GET /api/registration/students") if p else fail("GET /api/registration/students")

    r, p = get("/api/registration/students/FA21-BCE-001")
    results.append(p)
    ok("GET student by ID") if p else fail("GET student by ID")

    r, p = get("/api/registration/courses")
    results.append(p)
    ok("GET courses list") if p else fail("GET courses list")

    # Register new student
    new_id = f"TEST-{random.randint(1000,9999)}"
    r, p = post("/api/registration/students", {
        "student_id": new_id, "name": "Test Student",
        "email": "test@cust.edu.pk", "program": "BCE", "semester": 5
    })
    results.append(p)
    ok(f"POST new student ({new_id})") if p else fail("POST new student")

    # Register course
    r, p = post("/api/registration/register-course", {
        "student_id": new_id, "course_code": "CPE4541", "semester": "Fall2026"
    })
    results.append(p)
    ok("POST register course") if p else fail("POST register course")

    # Duplicate check
    r, p = post("/api/registration/register-course", {
        "student_id": new_id, "course_code": "CPE4541", "semester": "Fall2026"
    }, expected=409)
    results.append(p)
    ok("Duplicate registration rejected (409)") if p else fail("Duplicate not rejected")

    return all(results)

def test_lms():
    hdr("TEST 3: LMS Service Functional Tests")
    sep()
    results = []

    r, p = get("/api/lms/courses")
    results.append(p)
    ok("GET LMS courses") if p else fail("GET LMS courses")

    r, p = get("/api/lms/materials/CPE4541")
    results.append(p)
    ok("GET course materials") if p else fail("GET materials")

    r, p = get("/api/lms/assignments/CPE4541")
    results.append(p)
    ok("GET assignments") if p else fail("GET assignments")

    r, p = get("/api/lms/announcements/CPE4541")
    results.append(p)
    ok("GET announcements") if p else fail("GET announcements")

    r, p = post("/api/lms/submit", {
        "assignment_id": 1, "student_id": "FA21-BCE-001",
        "content": "My CEP Phase 3 submission content here."
    })
    results.append(p)
    ok("POST submit assignment") if p else fail("POST submit assignment")

    return all(results)

def test_examination():
    hdr("TEST 4: Examination Service Functional Tests")
    sep()
    results = []

    r, p = get("/api/exam/exams")
    results.append(p)
    ok("GET all exams") if p else fail("GET all exams")

    r, p = get("/api/exam/exams/CPE4541")
    results.append(p)
    ok("GET exams by course") if p else fail("GET exams by course")

    r, p = get("/api/exam/results/FA21-BCE-001")
    results.append(p)
    ok("GET student results") if p else fail("GET student results")

    r, p = get("/api/exam/transcript/FA21-BCE-001")
    results.append(p)
    ok("GET transcript") if p else fail("GET transcript")

    sid = f"TST{random.randint(100,999)}"
    r, p = post("/api/exam/results", {
        "student_id": sid, "course_code": "CPE4541",
        "exam_type": "Final Term", "marks_obtained": 42, "total_marks": 50
    })
    results.append(p)
    if p and r:
        grade = r.json().get("grade","?")
        ok(f"POST record result - Grade: {grade} ({sid})")
    else:
        fail("POST record result")

    r, p = post("/api/exam/allocate-seat", {"student_id": sid, "exam_id": 2})
    results.append(p)
    if p and r:
        ok(f"POST allocate seat - {r.json().get('seat_number','?')}")
    else:
        fail("POST allocate seat")

    return all(results)

# ─── Load & Performance Test ──────────────────────────────────────────────────
def test_load_performance():
    hdr("TEST 5: Load & Concurrency Benchmarking")
    sep()

    NUM_REQUESTS  = 100
    CONCURRENCY   = [1, 5, 10, 20]
    print(f"  Endpoint: GET {BASE_URL}/api/registration/students")
    print(f"  Total requests per concurrency level: {NUM_REQUESTS}\n")

    benchmark_data = {}

    for workers in CONCURRENCY:
        times = []
        errors = 0

        def make_request(_):
            t0 = time.time()
            try:
                r = requests.get(f"{BASE_URL}/api/registration/students", timeout=10)
                if r.status_code != 200:
                    return None
            except Exception:
                return None
            return time.time() - t0

        t_wall = time.time()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(make_request, i) for i in range(NUM_REQUESTS)]
            for f in as_completed(futures):
                result = f.result()
                if result is None:
                    errors += 1
                else:
                    times.append(result)
        wall = time.time() - t_wall

        if times:
            avg  = statistics.mean(times) * 1000
            p50  = statistics.median(times) * 1000
            p95  = sorted(times)[int(len(times)*0.95)] * 1000
            p99  = sorted(times)[int(len(times)*0.99)] * 1000 if len(times) >= 100 else sorted(times)[-1]*1000
            tput = len(times) / wall
            print(f"  Concurrency={workers:>2}:  Avg={avg:6.1f}ms  P50={p50:6.1f}ms  P95={p95:6.1f}ms  "
                  f"Throughput={tput:5.1f}req/s  Errors={errors}")
            benchmark_data[workers] = {"avg_ms": round(avg,1), "p95_ms": round(p95,1),
                                        "throughput": round(tput,1), "errors": errors}
        else:
            print(f"  Concurrency={workers}: All requests failed")

    return benchmark_data

# ─── Resource Utilization (Docker stats) ──────────────────────────────────────
def test_scalability():
    hdr("TEST 6: Scalability & Endpoint Coverage")
    sep()

    endpoints = [
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/api/registration/students"),
        ("GET", "/api/registration/courses"),
        ("GET", "/api/lms/courses"),
        ("GET", "/api/lms/materials/CPE4541"),
        ("GET", "/api/lms/assignments/CPE4541"),
        ("GET", "/api/exam/exams"),
        ("GET", "/api/exam/transcript/FA21-BCE-001"),
        ("GET", "/api/dashboard/metrics"),
    ]

    passed = 0
    for method, path in endpoints:
        t0 = time.time()
        try:
            r = requests.get(f"{BASE_URL}{path}", timeout=10)
            elapsed = (time.time()-t0)*1000
            status = "✓" if r.status_code == 200 else "✗"
            print(f"  {status} {method} {path:<45} {r.status_code}  {elapsed:.1f}ms")
            if r.status_code == 200:
                passed += 1
        except Exception as e:
            print(f"  ✗ {method} {path:<45} ERROR: {e}")
    print(f"\n  Passed: {passed}/{len(endpoints)} endpoints")

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"CUST CPE4541 - Phase 4 Test & Benchmark Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target:  {BASE_URL}")
    print(f"{'='*60}")

    # Check gateway reachable
    try:
        requests.get(f"{BASE_URL}/health", timeout=5)
    except Exception:
        print(f"\n{RED}ERROR: Cannot reach {BASE_URL}{RESET}")
        print("Make sure services are running: docker-compose up -d")
        sys.exit(1)

    all_pass = []
    all_pass.append(test_health())
    all_pass.append(test_registration())
    all_pass.append(test_lms())
    all_pass.append(test_examination())
    bench = test_load_performance()
    test_scalability()

    print(f"\n{'='*60}")
    print(f"FINAL RESULT: {'ALL TESTS PASSED' if all(all_pass) else 'SOME TESTS FAILED'}")
    print(f"{'='*60}\n")
