"""Performance Benchmark: Full Rebuild vs Incremental Ingestion Engine."""

import time
import tracemalloc
from stage1.atlas import StudyGraph
from stage3.watch import StudyWatch
from stage3.ingestion import IncrementalIngestionEngine


def benchmark():
    print("=== BENCHMARK: FULL REBUILD vs INCREMENTAL SURVEILLANCE ===")

    # 1. Measure Initial Full Build
    tracemalloc.start()
    t0 = time.perf_counter()
    g_full = StudyGraph("hackathon-data")
    stats_c1 = g_full.build(cut=1)
    full_build_c1_ms = round((time.perf_counter() - t0) * 1000, 2)
    mem_current, mem_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Initial Cut 1 Build Time: {full_build_c1_ms} ms")
    print(f"Initial Cut 1 Records: {stats_c1['records']}")
    print(f"Initial Peak Memory: {mem_peak / (1024 * 1024):.2f} MB")

    # 2. Compare Sequential Full Rebuild vs Sequential Incremental Updates across Cuts 2..6
    full_times = []
    incremental_times = []
    records_touched = []
    findings_recomputed = []

    # Incremental watch instance
    watch = StudyWatch(data_dir="hackathon-data", deterministic_clock=True)

    for c in range(2, 7):
        # Full rebuild time
        t_start = time.perf_counter()
        g_temp = StudyGraph("hackathon-data")
        g_temp.build(cut=c)
        full_ms = round((time.perf_counter() - t_start) * 1000, 2)
        full_times.append(full_ms)

        # Incremental time
        t_inc = time.perf_counter()
        rep = watch.run_cut(c)
        inc_ms = rep["elapsed_ms"]
        incremental_times.append(inc_ms)
        m = rep["metrics"]
        records_touched.append(m["records_examined"])
        findings_recomputed.append(m["findings_recomputed"])

        print(
            f"Cut {c}: Full Rebuild = {full_ms:6.1f} ms | "
            f"Incremental = {inc_ms:6.1f} ms | "
            f"Examined = {m['records_examined']:4d} | "
            f"Inserted = {m['records_inserted']:4d} | "
            f"Corrected = {m['corrected_records']:3d} | "
            f"Findings Recomputed = {m['findings_recomputed']:3d}"
        )

    avg_full = sum(full_times) / len(full_times)
    avg_inc = sum(incremental_times) / len(incremental_times)
    speedup = avg_full / avg_inc if avg_inc > 0 else 1.0

    print("\n=== SUMMARY RESULTS ===")
    print(f"Average Full Rebuild Time per Cut: {avg_full:.1f} ms")
    print(f"Average Incremental Time per Cut:   {avg_inc:.1f} ms")
    print(f"Performance Speedup:               {speedup:.2f}x faster")
    print(f"Total Budget Used (Cuts 1-6):      {watch.budget_used_units:.1f} units (Tier: {watch.current_budget_tier.value})")


if __name__ == "__main__":
    benchmark()
