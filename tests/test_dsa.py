"""
Unit Tests for Custom DSA Layer.

Covers:
- MinHeap: Priority ordering, arrival timestamp tie-breaking, priority updates (up & down),
  arbitrary removal (including middle and edge cases), empty heap behaviors, and non-destructive sorted lists.
- LinkedList: Append, prepend, remove (head, middle, tail, predicate), find, to_list, and size.
- FIFO Queue: Strict FIFO ordering, peek, empty handling, and to_list.
- HashMap: Put, get, update, remove, collisions, dynamic resizing at load factor > 0.75, and Pythonic operators.
"""

import pytest
from dsa.min_heap import MinHeap
from dsa.linked_list import LinkedList
from dsa.queue import Queue
from dsa.hash_utils import HashMap


# ============================================================================
# 1. MinHeap Tests
# ============================================================================

def test_heap_ordering_by_priority():
    """Verify patients are extracted strictly in order of medical priority (1=Critical ... 4=Minor)."""
    heap = MinHeap()
    # (priority, arrival_ts, patient_id)
    heap.insert(3, 100.0, "P_MODERATE")
    heap.insert(1, 102.0, "P_CRITICAL")
    heap.insert(4, 101.0, "P_MINOR")
    heap.insert(2, 103.0, "P_URGENT")

    assert heap.size() == 4
    assert heap.peek() == (1, 102.0, "P_CRITICAL")

    extracted = []
    while not heap.is_empty():
        extracted.append(heap.extract_min())

    assert [item[2] for item in extracted] == ["P_CRITICAL", "P_URGENT", "P_MODERATE", "P_MINOR"]
    assert [item[0] for item in extracted] == [1, 2, 3, 4]
    assert heap.size() == 0


def test_heap_tie_break_by_arrival_time():
    """Verify that patients with the same priority are served strictly FIFO (earlier timestamp first)."""
    heap = MinHeap()
    heap.insert(2, 200.0, "P_URGENT_LATER")
    heap.insert(2, 150.0, "P_URGENT_EARLIEST")
    heap.insert(2, 175.0, "P_URGENT_MIDDLE")

    extracted = []
    while not heap.is_empty():
        extracted.append(heap.extract_min())

    assert [item[2] for item in extracted] == [
        "P_URGENT_EARLIEST",
        "P_URGENT_MIDDLE",
        "P_URGENT_LATER",
    ]


def test_heap_mixed_priority_and_timestamp_ordering():
    """Verify combination of priority and arrival timestamp tie-breaking."""
    heap = MinHeap()
    heap.insert(2, 10.0, "P2_10")
    heap.insert(1, 50.0, "P1_50")  # Critical should come before Urgent even with later arrival
    heap.insert(2, 5.0, "P2_5")    # Urgent with earlier arrival
    heap.insert(1, 20.0, "P1_20")  # Critical with earlier arrival

    order = [heap.extract_min()[2] for _ in range(4)]
    assert order == ["P1_20", "P1_50", "P2_5", "P2_10"]


def test_heap_update_priority_moving_up():
    """Verify changing a patient to a more critical priority moves them up to the root."""
    heap = MinHeap()
    heap.insert(3, 100.0, "P1")
    heap.insert(4, 101.0, "P2")
    heap.insert(2, 102.0, "P3")

    # Current top should be P3 (priority 2)
    assert heap.peek()[2] == "P3"

    # Escalate P2 from priority 4 (Minor) to 1 (Critical)
    heap.update_priority("P2", 1)

    assert heap.peek()[2] == "P2"
    assert heap.extract_min() == (1, 101.0, "P2")


def test_heap_update_priority_moving_down():
    """Verify changing a patient to a less critical priority moves them down."""
    heap = MinHeap()
    heap.insert(1, 100.0, "P1")
    heap.insert(2, 105.0, "P2")
    heap.insert(3, 110.0, "P3")

    assert heap.peek()[2] == "P1"

    # De-escalate P1 from priority 1 to priority 4
    heap.update_priority("P1", 4)

    # Now P2 should be the new top
    assert heap.peek()[2] == "P2"
    order = [heap.extract_min()[2] for _ in range(3)]
    assert order == ["P2", "P3", "P1"]


def test_heap_remove_from_middle():
    """Verify removing a patient located in the middle of the heap preserves heap validity."""
    heap = MinHeap()
    patients = [
        (1, 10.0, "P1"),
        (2, 20.0, "P2"),
        (2, 25.0, "P3"),
        (3, 30.0, "P4"),
        (4, 40.0, "P5"),
    ]
    for p, ts, pid in patients:
        heap.insert(p, ts, pid)

    # Remove P3 from the middle
    removed = heap.remove("P3")
    assert removed == (2, 25.0, "P3")
    assert not heap.contains("P3")
    assert heap.size() == 4

    remaining = [heap.extract_min()[2] for _ in range(4)]
    assert remaining == ["P1", "P2", "P4", "P5"]


def test_heap_remove_edge_cases():
    """Verify edge cases of removal: root, last item, single item, and non-existent key."""
    heap = MinHeap()
    heap.insert(2, 100.0, "ONLY")
    assert heap.remove("ONLY") == (2, 100.0, "ONLY")
    assert heap.is_empty()
    assert not heap.contains("ONLY")

    # Removing non-existent patient raises KeyError
    with pytest.raises(KeyError):
        heap.remove("NON_EXISTENT")

    with pytest.raises(KeyError):
        heap.update_priority("NON_EXISTENT", 1)


def test_heap_empty_edge_cases():
    """Verify empty heap operations return None safely."""
    heap = MinHeap()
    assert heap.is_empty()
    assert heap.size() == 0
    assert heap.peek() is None
    assert heap.extract_min() is None


def test_heap_duplicate_patient_raises():
    """Inserting the same patient_id twice should raise ValueError."""
    heap = MinHeap()
    heap.insert(1, 100.0, "P_DUP")
    with pytest.raises(ValueError):
        heap.insert(2, 105.0, "P_DUP")


def test_heap_to_sorted_list_non_destructive():
    """Verify to_sorted_list() returns elements in order without modifying the heap."""
    heap = MinHeap()
    heap.insert(3, 10.0, "P3")
    heap.insert(1, 20.0, "P1")
    heap.insert(2, 15.0, "P2")

    sorted_list = heap.to_sorted_list()
    assert [item[2] for item in sorted_list] == ["P1", "P2", "P3"]

    # Verify the original heap is intact and untouched
    assert heap.size() == 3
    assert heap.peek()[2] == "P1"


# ============================================================================
# 2. FIFO Queue Tests
# ============================================================================

def test_queue_fifo_order():
    """Verify strict First-In, First-Out queue ordering for available doctors."""
    q = Queue()
    q.enqueue("Dr. Alice")
    q.enqueue("Dr. Bob")
    q.enqueue("Dr. Charlie")

    assert q.size() == 3
    assert q.peek() == "Dr. Alice"

    assert q.dequeue() == "Dr. Alice"
    assert q.dequeue() == "Dr. Bob"
    assert q.dequeue() == "Dr. Charlie"
    assert q.dequeue() is None
    assert q.is_empty()


def test_queue_peek_and_to_list():
    """Verify queue peek does not mutate state and to_list preserves order."""
    q = Queue()
    assert q.peek() is None
    q.enqueue("Doc1")
    q.enqueue("Doc2")

    assert q.peek() == "Doc1"
    assert q.size() == 2
    assert q.to_list() == ["Doc1", "Doc2"]
    assert [d for d in q] == ["Doc1", "Doc2"]


# ============================================================================
# 3. Singly LinkedList Tests
# ============================================================================

def test_linked_list_append_and_prepend():
    """Verify append and prepend operations maintain correct sequence."""
    ll = LinkedList()
    ll.append({"status": "TRIAGED", "note": "Arrived at ER"})
    ll.append({"status": "ASSIGNED", "note": "Assigned to Dr. House"})
    ll.prepend({"status": "ADMITTED", "note": "Front desk check-in"})

    assert ll.size() == 3
    statuses = [entry["status"] for entry in ll.to_list()]
    assert statuses == ["ADMITTED", "TRIAGED", "ASSIGNED"]


def test_linked_list_remove_operations():
    """Verify removal from head, middle, and tail, as well as predicate removal."""
    ll = LinkedList()
    for val in [10, 20, 30, 40, 50]:
        ll.append(val)

    # Remove head (10)
    assert ll.remove(10) is True
    assert ll.to_list() == [20, 30, 40, 50]

    # Remove middle (30)
    assert ll.remove(30) is True
    assert ll.to_list() == [20, 40, 50]

    # Remove tail (50)
    assert ll.remove(50) is True
    assert ll.to_list() == [20, 40]

    # Remove non-existent element
    assert ll.remove(999) is False
    assert ll.size() == 2

    # Remove using predicate
    assert ll.remove(lambda x: x == 40) is True
    assert ll.to_list() == [20]


def test_linked_list_find():
    """Verify finding elements by value and by predicate."""
    ll = LinkedList()
    ll.append({"id": 1, "note": "First entry"})
    ll.append({"id": 2, "note": "Second entry"})

    found = ll.find(lambda x: x["id"] == 2)
    assert found == {"id": 2, "note": "Second entry"}

    not_found = ll.find(lambda x: x["id"] == 99)
    assert not_found is None


# ============================================================================
# 4. HashMap Tests
# ============================================================================

def test_hashmap_put_get_update():
    """Verify basic key-value insertion, retrieval, and updates."""
    hm = HashMap(initial_capacity=8)
    hm.put("P1", {"name": "Alice", "age": 30})
    hm.put("P2", {"name": "Bob", "age": 45})

    assert hm.size() == 2
    assert hm.get("P1")["name"] == "Alice"
    assert hm.get("P2")["name"] == "Bob"
    assert hm.get("P_UNKNOWN") is None
    assert hm.get("P_UNKNOWN", default="DEFAULT") == "DEFAULT"

    # Update P1
    hm.put("P1", {"name": "Alice Cooper", "age": 31})
    assert hm.size() == 2
    assert hm.get("P1")["name"] == "Alice Cooper"


def test_hashmap_remove_and_contains():
    """Verify contains check and removal handling."""
    hm = HashMap(initial_capacity=8)
    hm.put("D1", "Dr. Strange")
    hm.put("D2", "Dr. Watson")

    assert hm.contains("D1")
    assert not hm.contains("D3")

    removed = hm.remove("D1")
    assert removed == "Dr. Strange"
    assert not hm.contains("D1")
    assert hm.size() == 1

    with pytest.raises(KeyError):
        hm.remove("D_NOT_FOUND")


def test_hashmap_collisions():
    """Verify correct operation when multiple keys collide into the same bucket."""
    hm = HashMap(initial_capacity=4)
    # Monkeypatch _hash to force all keys to bucket 0 to simulate extreme collision
    original_hash = hm._hash
    hm._hash = lambda key: 0

    hm.put("k1", "v1")
    hm.put("k2", "v2")
    hm.put("k3", "v3")

    assert hm.get("k1") == "v1"
    assert hm.get("k2") == "v2"
    assert hm.get("k3") == "v3"
    assert hm.contains("k2")
    assert hm.remove("k2") == "v2"
    assert not hm.contains("k2")
    assert hm.get("k1") == "v1"
    assert hm.get("k3") == "v3"


def test_hashmap_resize_at_load_factor():
    """Verify that HashMap doubles its capacity when load factor exceeds 0.75."""
    hm = HashMap(initial_capacity=4, load_factor_threshold=0.75)
    # Threshold for 4 buckets is 4 * 0.75 = 3 items.
    # Inserting 4th item must trigger resize to capacity 8.
    hm.put("item1", 1)
    hm.put("item2", 2)
    hm.put("item3", 3)
    assert hm._capacity == 4

    # 4th item triggers resize
    hm.put("item4", 4)
    assert hm._capacity == 8
    assert hm.size() == 4

    # Insert more to trigger another resize (8 * 0.75 = 6)
    for i in range(5, 15):
        hm.put(f"item{i}", i)

    assert hm.size() == 14
    assert hm._capacity >= 16

    # Verify all items remain intact and accessible after multiple resizes
    for i in range(1, 15):
        assert hm.get(f"item{i}") == i


def test_hashmap_dunder_methods():
    """Verify idiomatic dictionary-like behavior with Python dunder methods."""
    hm = HashMap()
    hm["patient_101"] = "Critical Condition"
    assert "patient_101" in hm
    assert hm["patient_101"] == "Critical Condition"
    assert len(hm) == 1

    del hm["patient_101"]
    assert "patient_101" not in hm
    assert len(hm) == 0
