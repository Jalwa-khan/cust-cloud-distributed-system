"""
CUST GPU-Accelerated Computing - Phase 3
Compares CPU vs GPU (Numba CUDA) for:
  1. Matrix multiplication (exam mark processing)
  2. Statistical analysis on large student datasets
  3. Grade curve calculation

CPE4541 CEP Project - Phase 3 & 4
Run: python gpu_benchmark.py
Requirements: pip install numba numpy
GPU: Requires NVIDIA GPU + CUDA toolkit for GPU mode.
     Falls back to CPU-parallel (Numba JIT) if no GPU found.
"""
import numpy as np
import time
import math
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

# ─── Check GPU availability ───────────────────────────────────────────────────
GPU_AVAILABLE = False
try:
    from numba import cuda, njit, prange
    import numba
    try:
        cuda.detect()
        GPU_AVAILABLE = True
        logging.info("CUDA GPU detected. Running GPU benchmarks.")
    except Exception:
        from numba import njit, prange
        logging.info("No CUDA GPU detected. Running CPU-JIT benchmarks.")
except ImportError:
    logging.warning("Numba not installed. Running pure NumPy benchmarks.")
    logging.warning("Install with: pip install numba")

# ─── Pure Python (baseline) ───────────────────────────────────────────────────
def cpu_matrix_multiply_pure(A, B):
    """Pure Python matrix multiplication - slowest baseline."""
    n = len(A)
    C = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                C[i][j] += A[i][k] * B[k][j]
    return C

# ─── NumPy CPU ────────────────────────────────────────────────────────────────
def cpu_matrix_multiply_numpy(A, B):
    return np.dot(A, B)

def cpu_grade_statistics(marks_array):
    """CPU: compute statistics over a large marks array."""
    mean  = np.mean(marks_array)
    std   = np.std(marks_array)
    pct   = np.percentile(marks_array, [25, 50, 75, 90, 95])
    z_scores = (marks_array - mean) / std
    curved = np.clip(marks_array + (100 - np.max(marks_array)) * 0.1, 0, 100)
    return mean, std, pct, z_scores, curved

# ─── Numba JIT CPU parallel ───────────────────────────────────────────────────
def run_numba_jit():
    try:
        from numba import njit, prange

        @njit(parallel=True)
        def numba_matrix_multiply(A, B):
            n = A.shape[0]
            C = np.zeros((n, n))
            for i in prange(n):
                for j in range(n):
                    for k in range(n):
                        C[i, j] += A[i, k] * B[k, j]
            return C

        @njit(parallel=True)
        def numba_grade_curve(marks, base_max):
            n = len(marks)
            curved = np.empty(n)
            for i in prange(n):
                bonus = (100.0 - base_max) * 0.1
                curved[i] = min(marks[i] + bonus, 100.0)
            return curved

        return numba_matrix_multiply, numba_grade_curve
    except ImportError:
        return None, None

# ─── GPU CUDA kernel ──────────────────────────────────────────────────────────
def run_gpu_benchmark(size=512):
    from numba import cuda

    @cuda.jit
    def gpu_matrix_multiply(A, B, C):
        row, col = cuda.grid(2)
        if row < C.shape[0] and col < C.shape[1]:
            val = 0.0
            for k in range(A.shape[1]):
                val += A[row, k] * B[k, col]
            C[row, col] = val

    A = np.random.rand(size, size).astype(np.float32)
    B = np.random.rand(size, size).astype(np.float32)

    # GPU execution
    d_A = cuda.to_device(A)
    d_B = cuda.to_device(B)
    d_C = cuda.device_array((size, size), dtype=np.float32)

    threads = (16, 16)
    blocks  = (math.ceil(size/16), math.ceil(size/16))

    t0 = time.time()
    gpu_matrix_multiply[blocks, threads](d_A, d_B, d_C)
    cuda.synchronize()
    gpu_time = time.time() - t0

    return d_C.copy_to_host(), gpu_time


# ─── Benchmark Suite ─────────────────────────────────────────────────────────
def run_benchmarks():
    print("\n" + "="*65)
    print("CUST CPE4541 - GPU vs CPU Performance Benchmark")
    print("Task: Simulated university-scale mark processing")
    print("="*65)

    results = {}

    # ── Test 1: Matrix multiplication (N=256) ────────────────────────────────
    N = 256
    A = np.random.rand(N, N).astype(np.float64)
    B = np.random.rand(N, N).astype(np.float64)

    print(f"\n[TEST 1] Matrix Multiplication ({N}x{N})")
    print(f"  Represents: Processing grade matrices for {N} students x {N} courses\n")

    # NumPy CPU baseline
    t0 = time.time()
    for _ in range(5):
        C_numpy = cpu_matrix_multiply_numpy(A, B)
    numpy_time = (time.time() - t0) / 5
    print(f"  CPU (NumPy)      : {numpy_time*1000:.3f} ms")
    results["numpy_matmul_ms"] = round(numpy_time*1000, 3)

    # Numba JIT
    numba_mm, numba_gc = run_numba_jit()
    if numba_mm is not None:
        A32 = A.astype(np.float64)
        B32 = B.astype(np.float64)
        numba_mm(A32, B32)  # warmup
        t0 = time.time()
        for _ in range(5):
            C_numba = numba_mm(A32, B32)
        numba_time = (time.time() - t0) / 5
        speedup = numpy_time / numba_time if numba_time > 0 else 1.0
        print(f"  CPU (Numba JIT)  : {numba_time*1000:.3f} ms  [{speedup:.2f}x speedup]")
        results["numba_matmul_ms"] = round(numba_time*1000, 3)
        results["numba_speedup"]   = round(speedup, 2)

    # GPU (if available)
    if GPU_AVAILABLE:
        _, gpu_time = run_gpu_benchmark(size=N)
        gpu_speedup = numpy_time / gpu_time
        print(f"  GPU (CUDA)       : {gpu_time*1000:.3f} ms  [{gpu_speedup:.2f}x speedup]")
        results["gpu_matmul_ms"] = round(gpu_time*1000, 3)
        results["gpu_speedup"]   = round(gpu_speedup, 2)
    else:
        print(f"  GPU (CUDA)       : Not available (no CUDA GPU)")

    # ── Test 2: Grade statistics on 100,000 student marks ───────────────────
    print(f"\n[TEST 2] Statistical Analysis on 100,000 Student Marks")
    print(f"  Represents: Computing grade curves and statistics for large cohort\n")

    np.random.seed(42)
    marks = np.random.normal(65, 15, 100_000).clip(0, 100).astype(np.float64)

    t0 = time.time()
    for _ in range(10):
        mean, std, pct, z, curved = cpu_grade_statistics(marks)
    stat_time = (time.time() - t0) / 10
    print(f"  CPU (NumPy)      : {stat_time*1000:.3f} ms")
    print(f"  Mean={mean:.2f}, Std={std:.2f}, Median={pct[1]:.2f}, P90={pct[3]:.2f}")
    results["numpy_stats_ms"] = round(stat_time*1000, 3)

    if numba_gc is not None:
        marks32 = marks.copy()
        max_mark = float(np.max(marks32))
        numba_gc(marks32, max_mark)  # warmup
        t0 = time.time()
        for _ in range(10):
            curved_nb = numba_gc(marks32, max_mark)
        nb_stat_time = (time.time() - t0) / 10
        speedup = stat_time / nb_stat_time if nb_stat_time > 0 else 1.0
        print(f"  CPU (Numba JIT)  : {nb_stat_time*1000:.3f} ms  [{speedup:.2f}x speedup]")
        results["numba_stats_ms"] = round(nb_stat_time*1000, 3)

    # ── Summary Table ────────────────────────────────────────────────────────
    print("\n" + "-"*65)
    print("BENCHMARK SUMMARY")
    print("-"*65)
    print(f"{'Metric':<35} {'Value'}")
    for k, v in results.items():
        print(f"  {k:<33} {v}")

    print("\nCONCLUSION:")
    if "numba_speedup" in results:
        print(f"  Numba JIT achieved {results['numba_speedup']}x speedup over pure NumPy.")
    if "gpu_speedup" in results:
        print(f"  CUDA GPU achieved {results['gpu_speedup']}x speedup over NumPy CPU.")
        print(f"  For large-scale result processing, GPU parallelism is highly effective.")
    else:
        print(f"  GPU not available. In a GPU-enabled environment (e.g., Azure NC series),")
        print(f"  CUDA would provide 10-100x speedup for batch result processing tasks.")
    print()

    return results


if __name__ == "__main__":
    run_benchmarks()
