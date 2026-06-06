"""
CUST Distributed Computing - MPI Operations (using mpi4py)
Simulates distributed grade processing across multiple nodes:
  - Broadcast: Professor broadcasts exam data to all nodes
  - Scatter: Distribute student records across processes
  - Gather: Collect results from all processes
  - Reduce: Calculate aggregate statistics

CPE4541 CEP Project - Phase 3
Run: mpiexec -n 4 python mpi_grade_processor.py
If mpi4py not installed: pip install mpi4py
"""
try:
    from mpi4py import MPI
    MPI_AVAILABLE = True
except ImportError:
    MPI_AVAILABLE = False
    print("[WARNING] mpi4py not installed. Running simulation mode.")
    print("[INFO]    Install with: pip install mpi4py")
    print()

import time
import json
import math
import random

# ─── Simulation fallback (no MPI) ────────────────────────────────────────────
def simulate_mpi_operations():
    """Simulate MPI operations without actual MPI for demonstration."""
    NUM_PROCESSES = 4
    print("=" * 60)
    print("CUST DISTRIBUTED GRADE PROCESSING - MPI SIMULATION")
    print(f"Simulating {NUM_PROCESSES} MPI processes")
    print("=" * 60)

    # Generate synthetic student data (anonymised)
    random.seed(42)
    all_students = [
        {"id": f"STU{i:03d}", "marks": random.uniform(40, 100), "course": "CPE4541"}
        for i in range(20)
    ]

    # ── BROADCAST: Root shares exam config to all processes ──────────────────
    print("\n[MPI BROADCAST] Process 0 broadcasting exam config to all nodes...")
    exam_config = {"total_marks": 100, "passing_marks": 45, "course": "CPE4541", "semester": "Spring2026"}
    for pid in range(NUM_PROCESSES):
        print(f"  Process {pid} received: {exam_config}")
    print(f"  Broadcast time: ~{0.002:.4f}s (simulated)")

    # ── SCATTER: Distribute student records evenly ────────────────────────────
    print("\n[MPI SCATTER] Distributing student records across processes...")
    chunk_size = len(all_students) // NUM_PROCESSES
    chunks = [all_students[i*chunk_size:(i+1)*chunk_size] for i in range(NUM_PROCESSES)]
    for pid, chunk in enumerate(chunks):
        ids = [s["id"] for s in chunk]
        print(f"  Process {pid} received {len(chunk)} students: {ids}")

    # ── PROCESS: Each node computes grades locally ───────────────────────────
    print("\n[LOCAL PROCESSING] Each process computes grades independently...")
    def calc_grade(marks):
        if marks >= 90: return "A"
        elif marks >= 80: return "B+"
        elif marks >= 70: return "B"
        elif marks >= 60: return "C+"
        elif marks >= 50: return "C"
        elif marks >= 45: return "D"
        else: return "F"

    process_results = []
    for pid, chunk in enumerate(chunks):
        t0 = time.time()
        result = [{"id": s["id"], "marks": round(s["marks"],2), "grade": calc_grade(s["marks"])} for s in chunk]
        elapsed = time.time() - t0
        print(f"  Process {pid}: processed {len(chunk)} records in {elapsed*1000:.2f}ms")
        process_results.append(result)

    # ── GATHER: Root collects all results ────────────────────────────────────
    print("\n[MPI GATHER] Collecting results from all processes to root (0)...")
    gathered = [r for chunk in process_results for r in chunk]
    print(f"  Root received {len(gathered)} total results")

    # ── REDUCE: Compute statistics ───────────────────────────────────────────
    print("\n[MPI REDUCE] Computing aggregate statistics (SUM/MIN/MAX/AVG)...")
    all_marks = [r["marks"] for r in gathered]
    total   = sum(all_marks)
    avg     = total / len(all_marks)
    minimum = min(all_marks)
    maximum = max(all_marks)
    passed  = sum(1 for m in all_marks if m >= exam_config["passing_marks"])
    print(f"  Total Students : {len(gathered)}")
    print(f"  Average Marks  : {avg:.2f}")
    print(f"  Minimum Marks  : {minimum:.2f}")
    print(f"  Maximum Marks  : {maximum:.2f}")
    print(f"  Pass Rate      : {passed}/{len(gathered)} ({passed/len(gathered)*100:.1f}%)")

    grade_dist = {}
    for r in gathered:
        grade_dist[r["grade"]] = grade_dist.get(r["grade"], 0) + 1
    print(f"  Grade Distribution: {dict(sorted(grade_dist.items()))}")
    print("\n[DONE] All MPI operations completed successfully.")
    return gathered

# ─── Real MPI Implementation ──────────────────────────────────────────────────
def run_with_mpi():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    def calc_grade(marks):
        if marks >= 90: return "A"
        elif marks >= 80: return "B+"
        elif marks >= 70: return "B"
        elif marks >= 60: return "C+"
        elif marks >= 50: return "C"
        elif marks >= 45: return "D"
        else: return "F"

    # ── BROADCAST ────────────────────────────────────────────────────────────
    exam_config = None
    if rank == 0:
        exam_config = {"total_marks": 100, "passing_marks": 45, "course": "CPE4541"}
        print(f"[Process 0] Broadcasting exam config: {exam_config}")
    exam_config = comm.bcast(exam_config, root=0)
    print(f"[Process {rank}] Received exam config via broadcast.")

    # ── SCATTER ───────────────────────────────────────────────────────────────
    random.seed(42)
    chunks = None
    if rank == 0:
        all_students = [{"id": f"STU{i:03d}", "marks": random.uniform(40,100)} for i in range(size * 5)]
        chunk_size = len(all_students) // size
        chunks = [all_students[i*chunk_size:(i+1)*chunk_size] for i in range(size)]
        print(f"[Process 0] Scattering {len(all_students)} students across {size} processes.")
    local_chunk = comm.scatter(chunks, root=0)
    print(f"[Process {rank}] Received {len(local_chunk)} students via scatter.")

    # ── LOCAL PROCESSING ──────────────────────────────────────────────────────
    local_results = [{"id": s["id"], "marks": round(s["marks"],2), "grade": calc_grade(s["marks"])} for s in local_chunk]

    # ── GATHER ────────────────────────────────────────────────────────────────
    all_results = comm.gather(local_results, root=0)
    if rank == 0:
        flat = [r for chunk in all_results for r in chunk]
        print(f"\n[Process 0] Gathered {len(flat)} results.")

        # ── REDUCE (manual) ───────────────────────────────────────────────────
        all_marks = [r["marks"] for r in flat]
        avg = sum(all_marks) / len(all_marks)
        print(f"[Process 0] REDUCE - Average marks: {avg:.2f}, Max: {max(all_marks):.2f}, Min: {min(all_marks):.2f}")
        passed = sum(1 for m in all_marks if m >= exam_config["passing_marks"])
        print(f"[Process 0] Pass Rate: {passed}/{len(flat)} ({passed/len(flat)*100:.1f}%)")

    # ── MPI REDUCE for sum ─────────────────────────────────────────────────────
    local_sum = sum(s["marks"] for s in local_chunk)
    global_sum = comm.reduce(local_sum, op=MPI.SUM, root=0)
    if rank == 0:
        print(f"[Process 0] MPI Reduce SUM check: {global_sum:.2f}")

    comm.Barrier()
    if rank == 0:
        print("\n[DONE] All MPI operations completed.")

# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if MPI_AVAILABLE:
        run_with_mpi()
    else:
        simulate_mpi_operations()
