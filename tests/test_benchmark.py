"""
Tests for DSA Benchmark API Endpoint.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_benchmark_endpoint_default():
    """Verify that /api/benchmark runs and returns performance data."""
    # Run with small N for quick unit test execution
    response = client.get("/api/benchmark?sizes=100,500")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    benchmark_data = data["data"]

    assert benchmark_data["sizes"] == [100, 500]
    assert len(benchmark_data["results"]) == 2

    first_trial = benchmark_data["results"][0]
    assert first_trial["n"] == 100
    assert "min_heap" in first_trial
    assert "sorted_list" in first_trial
    assert "linear_scan" in first_trial

    assert "insert_ms" in first_trial["min_heap"]
    assert "extract_ms" in first_trial["min_heap"]
    assert "total_ms" in first_trial["min_heap"]

    # Verify complexity documentation is returned
    complexities = benchmark_data["complexities"]
    assert "min_heap" in complexities
    assert "sorted_list" in complexities
    assert "linear_scan" in complexities
    assert complexities["min_heap"]["insert_time"] == "O(log N)"
    assert complexities["min_heap"]["extract_time"] == "O(log N)"
