"""
DSA Empirical Performance Benchmark Route.

Compares our hand-written Indexed Min-Heap against naive priority queue approaches:
1. Custom MinHeap: Binary heap with array storage and position index map.
2. Naive Sorted List: Appends item and re-sorts array on every insertion.
3. Naive Linear Scan: Inserts in O(1), but performs a linear scan to find minimum on extraction.
"""

import random
import time
from typing import List, Optional
from fastapi import APIRouter, Query
from backend.models import ApiResponse
from dsa.min_heap import MinHeap

router = APIRouter(prefix="/api/benchmark", tags=["Benchmark"])


def benchmark_trial(n: int) -> dict:
    """
    Executes a benchmark trial for N random patients across 3 DSA approaches.
    
    Generates synthetic patient records with random priorities (1-4) and timestamps.
    Times the insertion phase and extraction phase using time.perf_counter().
    """
    # Deterministic seed for reproducible comparisons across trials
    rng = random.Random(42 + n)
    test_data = [
        (rng.randint(1, 4), float(1000 + i), f"PAT_{i}")
        for i in range(n)
    ]

    # -------------------------------------------------------------------------
    # 1. Custom MinHeap (O(log n) insert, O(log n) extract)
    # -------------------------------------------------------------------------
    t_start = time.perf_counter()
    heap = MinHeap()
    for priority, arrival_ts, patient_id in test_data:
        heap.insert(priority, arrival_ts, patient_id)
    t_heap_insert = (time.perf_counter() - t_start) * 1000.0  # ms

    t_start = time.perf_counter()
    while not heap.is_empty():
        heap.extract_min()
    t_heap_extract = (time.perf_counter() - t_start) * 1000.0  # ms

    # -------------------------------------------------------------------------
    # 2. Naive Sorted List (Re-sort after every insert: O(n log n) per insert)
    # -------------------------------------------------------------------------
    t_start = time.perf_counter()
    sorted_list = []
    for item in test_data:
        sorted_list.append(item)
        sorted_list.sort(key=lambda x: (x[0], x[1]))
    t_sorted_insert = (time.perf_counter() - t_start) * 1000.0  # ms

    t_start = time.perf_counter()
    while sorted_list:
        sorted_list.pop(0)
    t_sorted_extract = (time.perf_counter() - t_start) * 1000.0  # ms

    # -------------------------------------------------------------------------
    # 3. Naive Linear Scan (O(1) insert, O(n) extract linear search)
    # -------------------------------------------------------------------------
    t_start = time.perf_counter()
    unsorted_list = []
    for item in test_data:
        unsorted_list.append(item)
    t_linear_insert = (time.perf_counter() - t_start) * 1000.0  # ms

    # For N <= 3000, perform full scan. For larger N, measure a sample of 500
    # extractions and scale proportionally to keep web response snappy.
    t_start = time.perf_counter()
    linear_copy = list(unsorted_list)
    if n <= 3000:
        while linear_copy:
            min_idx = 0
            for i in range(1, len(linear_copy)):
                if (linear_copy[i][0], linear_copy[i][1]) < (linear_copy[min_idx][0], linear_copy[min_idx][1]):
                    min_idx = i
            linear_copy.pop(min_idx)
        t_linear_extract = (time.perf_counter() - t_start) * 1000.0
    else:
        sample_k = 500
        for _ in range(sample_k):
            min_idx = 0
            for i in range(1, len(linear_copy)):
                if (linear_copy[i][0], linear_copy[i][1]) < (linear_copy[min_idx][0], linear_copy[min_idx][1]):
                    min_idx = i
            linear_copy.pop(min_idx)
        elapsed = (time.perf_counter() - t_start) * 1000.0
        # Extrapolate to full N
        t_linear_extract = elapsed * (n / sample_k)

    return {
        "n": n,
        "min_heap": {
            "insert_ms": round(t_heap_insert, 2),
            "extract_ms": round(t_heap_extract, 2),
            "total_ms": round(t_heap_insert + t_heap_extract, 2),
        },
        "sorted_list": {
            "insert_ms": round(t_sorted_insert, 2),
            "extract_ms": round(t_sorted_extract, 2),
            "total_ms": round(t_sorted_insert + t_sorted_extract, 2),
        },
        "linear_scan": {
            "insert_ms": round(t_linear_insert, 2),
            "extract_ms": round(t_linear_extract, 2),
            "total_ms": round(t_linear_insert + t_linear_extract, 2),
        },
    }


@router.get("", response_model=ApiResponse)
def get_benchmark_results(
    sizes: Optional[str] = Query("1000,5000,10000", description="Comma-separated patient quantities")
):
    """
    Executes an empirical DSA benchmark comparing MinHeap vs Sorted List vs Linear Scan.
    Returns insert, extract, and total elapsed execution time in milliseconds.
    """
    try:
        n_list = [int(s.strip()) for s in sizes.split(",") if s.strip().isdigit()]
        if not n_list:
            n_list = [1000, 5000, 10000]
    except Exception:
        n_list = [1000, 5000, 10000]

    # Limit maximum N to prevent denial-of-service / timeouts
    n_list = [min(max(100, n), 20000) for n in n_list]

    results = []
    for n in n_list:
        results.append(benchmark_trial(n))

    complexities = {
        "min_heap": {
            "name": "Custom MinHeap (Binary Tree in Array)",
            "insert_time": "O(log N)",
            "extract_time": "O(log N)",
            "update_time": "O(log N) via Position Map",
            "space": "O(N)",
            "verdict": "Optimal balanced priority queue. Maintains strict priority ordering efficiently as queue grows.",
        },
        "sorted_list": {
            "name": "Naive Sorted List (Re-sort on Insert)",
            "insert_time": "O(N log N)",
            "extract_time": "O(1)",
            "update_time": "O(N log N)",
            "space": "O(N)",
            "verdict": "Severely degrades as N increases due to repeated full array re-sorting on every single patient arrival.",
        },
        "linear_scan": {
            "name": "Naive Unsorted List (Linear Search on Extract)",
            "insert_time": "O(1)",
            "extract_time": "O(N)",
            "update_time": "O(1)",
            "space": "O(N)",
            "verdict": "Fast intake, but dangerous in an emergency triage setting because finding the next critical patient requires scanning all waiting records.",
        },
    }

    return ApiResponse(
        success=True,
        data={
            "sizes": n_list,
            "results": results,
            "complexities": complexities,
        },
        message="DSA benchmark completed successfully."
    )
