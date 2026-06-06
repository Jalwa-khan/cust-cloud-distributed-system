"""
CUST Distributed Computing - Multithreading
Simulates concurrent student requests during peak registration/exam periods
Demonstrates thread safety, locks, semaphores, and thread pools.
CPE4541 CEP Project - Phase 3
Run: python multithreaded_server.py
"""
import threading
import time
import random
import queue
import statistics
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(threadName)s] %(message)s")

# ─── Shared Resources ─────────────────────────────────────────────────────────
class RegistrationSystem:
    """Thread-safe registration system with locks and semaphores."""

    def __init__(self, course_capacity=30, max_concurrent=5):
        self.capacity = course_capacity
        self.enrolled = 0
        self.registrations = {}          # student_id -> course_code
        self.lock = threading.Lock()     # Protects enrolled counter
        self.semaphore = threading.Semaphore(max_concurrent)  # Limit concurrent access
        self.request_log = []
        self.log_lock = threading.Lock()
        self.response_times = []

    def register_student(self, student_id, course_code):
        """Thread-safe course registration."""
        t_start = time.time()
        self.semaphore.acquire()
        try:
            # Simulate DB/network latency
            time.sleep(random.uniform(0.01, 0.05))

            with self.lock:
                if student_id in self.registrations:
                    result = {"status": "error", "msg": "Already registered"}
                elif self.enrolled >= self.capacity:
                    result = {"status": "error", "msg": "Course full"}
                else:
                    self.enrolled += 1
                    self.registrations[student_id] = course_code
                    result = {"status": "success", "msg": f"Registered {student_id} for {course_code}",
                              "seat": self.enrolled}
        finally:
            self.semaphore.release()

        elapsed = time.time() - t_start
        with self.log_lock:
            self.request_log.append({"student": student_id, "result": result["status"], "time_ms": round(elapsed*1000,2)})
            self.response_times.append(elapsed)
        return result

    def get_stats(self):
        with self.lock:
            enrolled = self.enrolled
        with self.log_lock:
            total = len(self.request_log)
            success = sum(1 for r in self.request_log if r["result"]=="success")
            avg_t = statistics.mean(self.response_times) * 1000 if self.response_times else 0
            p95_t = sorted(self.response_times)[int(len(self.response_times)*0.95)-1]*1000 if self.response_times else 0
        return {
            "enrolled": enrolled,
            "capacity": self.capacity,
            "total_requests": total,
            "successful": success,
            "failed": total - success,
            "avg_response_ms": round(avg_t, 2),
            "p95_response_ms": round(p95_t, 2),
        }


# ─── Worker Functions ─────────────────────────────────────────────────────────
def student_registration_worker(system, student_id, course_code):
    """Simulates a student submitting a registration request."""
    result = system.register_student(student_id, course_code)
    return student_id, result


def exam_result_processor(student_id, marks, total):
    """Simulates processing exam results in parallel."""
    time.sleep(random.uniform(0.005, 0.02))  # Simulate computation
    grade_map = [(90,"A"),(80,"B+"),(70,"B"),(60,"C+"),(50,"C"),(45,"D")]
    pct = (marks / total) * 100
    grade = next((g for threshold, g in grade_map if pct >= threshold), "F")
    return {"student_id": student_id, "marks": marks, "percentage": round(pct,2), "grade": grade}


# ─── Demo: Peak Registration Load ─────────────────────────────────────────────
def demo_peak_registration():
    print("\n" + "="*60)
    print("DEMO 1: Peak Registration Period - Concurrent Requests")
    print("="*60)

    system = RegistrationSystem(course_capacity=20, max_concurrent=5)
    NUM_STUDENTS = 35  # More than capacity to test overflow

    students = [f"STU{i:03d}" for i in range(NUM_STUDENTS)]
    random.shuffle(students)

    t_start = time.time()
    with ThreadPoolExecutor(max_workers=10, thread_name_prefix="RegWorker") as executor:
        futures = {executor.submit(student_registration_worker, system, sid, "CPE4541"): sid
                   for sid in students}
        for future in as_completed(futures):
            sid, result = future.result()
            status = result["status"]
            msg = result["msg"]
            logging.info(f"Student {sid}: [{status.upper()}] {msg}")

    elapsed = time.time() - t_start
    stats = system.get_stats()

    print(f"\n--- Registration Summary ---")
    print(f"  Total students attempted : {stats['total_requests']}")
    print(f"  Successfully registered  : {stats['successful']}")
    print(f"  Rejected (full/duplicate): {stats['failed']}")
    print(f"  Enrolled / Capacity      : {stats['enrolled']} / {stats['capacity']}")
    print(f"  Total wall-clock time    : {elapsed:.3f}s")
    print(f"  Avg response time        : {stats['avg_response_ms']}ms")
    print(f"  P95 response time        : {stats['p95_response_ms']}ms")
    print(f"  Effective throughput     : {stats['total_requests']/elapsed:.1f} req/s")


# ─── Demo: Parallel Exam Result Processing ─────────────────────────────────────
def demo_parallel_result_processing():
    print("\n" + "="*60)
    print("DEMO 2: Parallel Exam Result Processing")
    print("="*60)

    random.seed(7)
    students = [{"id": f"STU{i:03d}", "marks": random.uniform(30, 100)} for i in range(50)]

    # Sequential
    t_seq = time.time()
    seq_results = [exam_result_processor(s["id"], s["marks"], 100) for s in students]
    seq_time = time.time() - t_seq

    # Parallel with ThreadPoolExecutor
    t_par = time.time()
    par_results = []
    with ThreadPoolExecutor(max_workers=8, thread_name_prefix="ResultWorker") as executor:
        futures = [executor.submit(exam_result_processor, s["id"], s["marks"], 100) for s in students]
        for f in as_completed(futures):
            par_results.append(f.result())
    par_time = time.time() - t_par

    print(f"  Students processed       : {len(students)}")
    print(f"  Sequential time          : {seq_time:.4f}s")
    print(f"  Parallel time (8 threads): {par_time:.4f}s")
    print(f"  Speedup                  : {seq_time/par_time:.2f}x")

    grades = {}
    for r in par_results:
        grades[r["grade"]] = grades.get(r["grade"],0) + 1
    print(f"  Grade Distribution       : {dict(sorted(grades.items()))}")


# ─── Demo: Producer-Consumer Queue ───────────────────────────────────────────
def demo_producer_consumer():
    print("\n" + "="*60)
    print("DEMO 3: Producer-Consumer - Notification Queue")
    print("="*60)

    notif_queue = queue.Queue(maxsize=20)
    results = []
    stop_event = threading.Event()

    def producer(name, count):
        """Produces university notifications."""
        notif_types = ["exam_schedule","result_publish","material_upload","deadline_reminder","system_alert"]
        for i in range(count):
            notif = {"id": f"{name}-{i}", "type": random.choice(notif_types),
                     "msg": f"Notification {i} from {name}", "ts": time.time()}
            notif_queue.put(notif)
            time.sleep(random.uniform(0.01, 0.03))
        logging.info(f"Producer {name} done.")

    def consumer(cid):
        """Consumes and processes notifications."""
        processed = 0
        while not stop_event.is_set() or not notif_queue.empty():
            try:
                notif = notif_queue.get(timeout=0.5)
                time.sleep(random.uniform(0.005, 0.015))  # Simulate processing
                results.append(notif)
                processed += 1
                notif_queue.task_done()
            except queue.Empty:
                continue
        logging.info(f"Consumer {cid} processed {processed} notifications.")

    # 3 producers, 5 consumers
    threads = []
    for i in range(3):
        t = threading.Thread(target=producer, args=(f"Producer-{i}", 15), name=f"Producer-{i}")
        threads.append(t)
    for i in range(5):
        t = threading.Thread(target=consumer, args=(i,), name=f"Consumer-{i}")
        threads.append(t)

    t_start = time.time()
    for t in threads: t.start()
    # Wait for producers first
    for t in threads[:3]: t.join()
    notif_queue.join()  # Wait for all items to be processed
    stop_event.set()
    for t in threads[3:]: t.join()
    elapsed = time.time() - t_start

    print(f"  Total notifications produced : 45 (3 producers x 15)")
    print(f"  Total notifications consumed : {len(results)}")
    print(f"  Wall-clock time              : {elapsed:.3f}s")
    print(f"  Throughput                   : {len(results)/elapsed:.1f} msg/s")


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\nCUST CPE4541 - Multithreading Demonstration")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    demo_peak_registration()
    demo_parallel_result_processing()
    demo_producer_consumer()
    print("\n[ALL DEMOS COMPLETE]")
