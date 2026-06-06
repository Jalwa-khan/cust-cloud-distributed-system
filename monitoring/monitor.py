"""
CUST CEP Phase 4 - Resource Monitoring
Collects Docker container stats and service metrics.
Run: python monitoring/monitor.py
"""
import subprocess
import json
import time
import requests
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000"
CONTAINERS = ["cust_gateway", "cust_registration", "cust_lms", "cust_examination"]

def get_docker_stats():
    """Get live Docker container resource usage."""
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format",
             '{"name":"{{.Name}}","cpu":"{{.CPUPerc}}","mem":"{{.MemUsage}}","net":"{{.NetIO}}","pids":"{{.PIDs}}"}'] +
            CONTAINERS,
            capture_output=True, text=True, timeout=10
        )
        stats = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    stats.append(json.loads(line))
                except: pass
        return stats
    except Exception as e:
        return [{"error": str(e)}]

def get_service_metrics():
    """Get application-level metrics from each service."""
    metrics = {}
    endpoints = {
        "registration": f"{BASE_URL}/api/registration/students",
        "lms":          f"{BASE_URL}/api/lms/courses",
        "examination":  f"{BASE_URL}/api/exam/exams",
    }
    for name, url in endpoints.items():
        t0 = time.time()
        try:
            r = requests.get(url, timeout=5)
            latency = (time.time()-t0)*1000
            metrics[name] = {"status": r.status_code, "latency_ms": round(latency,2)}
        except Exception as e:
            metrics[name] = {"status": "error", "error": str(e)}
    return metrics

def print_monitoring_table(docker_stats, app_metrics, iteration):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] Monitoring Snapshot #{iteration}")
    print(f"{'Container':<25} {'CPU%':<10} {'Memory':<20} {'Net I/O':<20} {'PIDs'}")
    print("-" * 85)
    for s in docker_stats:
        if "error" not in s:
            print(f"{s.get('name','?'):<25} {s.get('cpu','?'):<10} {s.get('mem','?'):<20} {s.get('net','?'):<20} {s.get('pids','?')}")

    print(f"\n{'Service':<20} {'HTTP Status':<15} {'Latency (ms)'}")
    print("-" * 50)
    for name, data in app_metrics.items():
        status = data.get("status","?")
        latency = data.get("latency_ms","N/A")
        print(f"  {name:<18} {str(status):<15} {latency}")

def main():
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    interval   = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"CUST CEP Phase 4 - Resource Monitor")
    print(f"Collecting {iterations} snapshots every {interval}s")
    print(f"Press Ctrl+C to stop\n")

    all_latencies = {"registration":[], "lms":[], "examination":[]}

    try:
        for i in range(1, iterations+1):
            docker_stats = get_docker_stats()
            app_metrics  = get_service_metrics()
            print_monitoring_table(docker_stats, app_metrics, i)
            for name, data in app_metrics.items():
                if "latency_ms" in data:
                    all_latencies[name].append(data["latency_ms"])
            if i < iterations:
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")

    # Summary
    print(f"\n{'='*50}")
    print("LATENCY SUMMARY (across all snapshots)")
    print(f"{'='*50}")
    for name, lats in all_latencies.items():
        if lats:
            import statistics
            print(f"  {name:<20} avg={statistics.mean(lats):.1f}ms  "
                  f"min={min(lats):.1f}ms  max={max(lats):.1f}ms")

if __name__ == "__main__":
    main()
