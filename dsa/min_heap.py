"""
Custom Min-Heap Implementation with Position Index Mapping (Indexed Min-Heap).

Designed for the Hospital Emergency and Patient Priority Management System.
Stores emergency patients ordered by medical urgency (priority: 1=Critical to 4=Minor),
breaking ties by earlier arrival timestamp (FIFO within the same priority level).

Maintains an internal position hash map (patient_id -> array index) to allow
priority updates and arbitrary node removals in O(log n) time.
"""

from typing import Any, List, Optional, Tuple


class MinHeap:
    """
    An array-based Indexed Min-Heap.
    
    Each element in the heap array is stored as a tuple:
        (priority: int, arrival_ts: float, patient_id: Any)
        
    Attributes:
        heap (List[Tuple[int, float, Any]]): The binary min-heap array.
        pos (dict): Mapping from patient_id to its current index in self.heap.
    """

    def __init__(self) -> None:
        """
        Initializes an empty Indexed Min-Heap.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        self.heap: List[Tuple[int, float, Any]] = []
        self.pos: dict = {}

    def is_empty(self) -> bool:
        """
        Checks whether the heap contains any elements.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            bool: True if empty, False otherwise.
        """
        return len(self.heap) == 0

    def size(self) -> int:
        """
        Returns the total number of elements currently in the heap.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            int: Number of elements in the heap.
        """
        return len(self.heap)

    def contains(self, patient_id: Any) -> bool:
        """
        Checks whether a patient is currently present in the heap.
        
        Time Complexity: O(1) average lookup via position hash map.
        Space Complexity: O(1)
        
        Args:
            patient_id: Unique identifier of the patient.
            
        Returns:
            bool: True if patient is in the heap, False otherwise.
        """
        return patient_id in self.pos

    def peek(self) -> Optional[Tuple[int, float, Any]]:
        """
        Returns the highest-priority patient tuple without removing it.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            Optional[Tuple[int, float, Any]]: The root element (priority, arrival_ts, patient_id),
                                             or None if the heap is empty.
        """
        if self.is_empty():
            return None
        return self.heap[0]

    def insert(self, priority: int, arrival_ts: float, patient_id: Any) -> None:
        """
        Inserts a new patient into the min-heap.
        
        The element is appended to the end of the array and bubbled up
        to restore the min-heap invariant.
        
        Time Complexity: O(log n) where n is the number of patients in the heap.
        Space Complexity: O(1) auxiliary space (O(n) total storage).
        
        Args:
            priority: Medical priority (1=Critical, 2=Urgent, 3=Moderate, 4=Minor).
            arrival_ts: Epoch timestamp of arrival.
            patient_id: Unique identifier for the patient.
            
        Raises:
            ValueError: If a patient with patient_id already exists in the heap.
        """
        if patient_id in self.pos:
            raise ValueError(f"Patient with ID '{patient_id}' already exists in the heap.")

        entry = (priority, arrival_ts, patient_id)
        self.heap.append(entry)
        index = len(self.heap) - 1
        self.pos[patient_id] = index
        self._heapify_up(index)

    def extract_min(self) -> Optional[Tuple[int, float, Any]]:
        """
        Removes and returns the highest priority patient from the heap.
        
        Replaces the root with the last element in the array, pops the last,
        and bubbles the new root down to restore the min-heap invariant.
        
        Time Complexity: O(log n) where n is the number of patients.
        Space Complexity: O(1) auxiliary space.
        
        Returns:
            Optional[Tuple[int, float, Any]]: The extracted minimum tuple, or None if empty.
        """
        if self.is_empty():
            return None

        min_item = self.heap[0]
        patient_id = min_item[2]

        if len(self.heap) == 1:
            self.heap.pop()
            del self.pos[patient_id]
            return min_item

        # Swap root with last element
        last_idx = len(self.heap) - 1
        self._swap(0, last_idx)

        # Remove the minimum item now at the end
        popped = self.heap.pop()
        del self.pos[popped[2]]

        # Bubble down the new root
        self._heapify_down(0)

        return popped

    def update_priority(self, patient_id: Any, new_priority: int) -> None:
        """
        Updates the priority level of an existing patient in the heap.
        
        Uses the position index map to locate the patient in O(1) time,
        updates the priority value, and then performs heapify up or down
        to restore the heap invariant.
        
        Time Complexity: O(log n) to restore heap property.
        Space Complexity: O(1) auxiliary space.
        
        Args:
            patient_id: Unique identifier of the patient to update.
            new_priority: New triage priority value (1=Critical ... 4=Minor).
            
        Raises:
            KeyError: If the patient is not found in the heap.
        """
        if patient_id not in self.pos:
            raise KeyError(f"Patient with ID '{patient_id}' not found in the heap.")

        idx = self.pos[patient_id]
        old_priority, arrival_ts, _ = self.heap[idx]
        self.heap[idx] = (new_priority, arrival_ts, patient_id)

        # Lower priority number means higher medical urgency:
        # If new_priority < old_priority, patient moves up (higher urgency).
        # If new_priority > old_priority, patient moves down (lower urgency).
        # Calling both handles all cases safely.
        self._heapify_up(idx)
        self._heapify_down(idx)

    def remove(self, patient_id: Any) -> Tuple[int, float, Any]:
        """
        Removes an arbitrary patient from the heap by patient_id.
        
        Uses the position map to find the element in O(1), swaps it with the
        last element, pops it, and restores the heap property in O(log n).
        
        Time Complexity: O(log n)
        Space Complexity: O(1) auxiliary space.
        
        Args:
            patient_id: Unique identifier of the patient to remove.
            
        Returns:
            Tuple[int, float, Any]: The removed patient tuple.
            
        Raises:
            KeyError: If patient_id is not in the heap.
        """
        if patient_id not in self.pos:
            raise KeyError(f"Patient with ID '{patient_id}' not found in the heap.")

        idx = self.pos[patient_id]
        last_idx = len(self.heap) - 1

        if idx == last_idx:
            popped = self.heap.pop()
            del self.pos[patient_id]
            return popped

        # Swap target element with last element
        self._swap(idx, last_idx)
        popped = self.heap.pop()
        del self.pos[patient_id]

        # Restore heap order for the swapped element now at idx
        self._heapify_up(idx)
        self._heapify_down(idx)

        return popped

    def to_sorted_list(self) -> List[Tuple[int, float, Any]]:
        """
        Returns a sorted list of all waiting patients in priority order without modifying the heap.
        
        Clones the internal heap array and position map, then iteratively extracts
        the minimum element to construct the exact waiting order.
        
        Time Complexity: O(n log n) where n is the number of elements in the heap.
        Space Complexity: O(n) to store the cloned heap and the sorted output list.
        
        Returns:
            List[Tuple[int, float, Any]]: List of patient tuples sorted by (priority, arrival_ts).
        """
        clone = MinHeap()
        clone.heap = list(self.heap)
        clone.pos = dict(self.pos)

        sorted_order: List[Tuple[int, float, Any]] = []
        while not clone.is_empty():
            sorted_order.append(clone.extract_min())

        return sorted_order

    def _swap(self, i: int, j: int) -> None:
        """
        Swaps elements at indices i and j in the heap array and synchronizes self.pos.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Args:
            i: First index.
            j: Second index.
        """
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
        self.pos[self.heap[i][2]] = i
        self.pos[self.heap[j][2]] = j

    def _compare(self, i: int, j: int) -> int:
        """
        Compares elements at index i and index j based on priority and arrival_ts.
        
        A patient has higher urgency (smaller key) if:
        1. Their priority number is smaller (1 is more critical than 2).
        2. If priority numbers are equal, the earlier arrival_ts is preferred.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            int: -1 if element i has higher urgency than element j,
                  1 if element i has lower urgency than element j,
                  0 if they have equal urgency.
        """
        p1, t1, id1 = self.heap[i]
        p2, t2, id2 = self.heap[j]

        if p1 != p2:
            return -1 if p1 < p2 else 1
        if t1 != t2:
            return -1 if t1 < t2 else 1
        
        # Consistent tie-break on ID if priority and timestamp are identical
        if id1 < id2:
            return -1
        elif id1 > id2:
            return 1
        return 0

    def _heapify_up(self, index: int) -> None:
        """
        Bubbles up the element at index until the min-heap property is satisfied.
        
        Time Complexity: O(log n) where n is the number of elements.
        Space Complexity: O(1) auxiliary space (iterative implementation).
        
        Args:
            index: Starting array index to bubble up.
        """
        while index > 0:
            parent = (index - 1) // 2
            if self._compare(index, parent) < 0:
                self._swap(index, parent)
                index = parent
            else:
                break

    def _heapify_down(self, index: int) -> None:
        """
        Bubbles down the element at index until the min-heap property is satisfied.
        
        Time Complexity: O(log n) where n is the number of elements.
        Space Complexity: O(1) auxiliary space (iterative implementation).
        
        Args:
            index: Starting array index to bubble down.
        """
        n = len(self.heap)
        while True:
            smallest = index
            left = 2 * index + 1
            right = 2 * index + 2

            if left < n and self._compare(left, smallest) < 0:
                smallest = left
            if right < n and self._compare(right, smallest) < 0:
                smallest = right

            if smallest != index:
                self._swap(index, smallest)
                index = smallest
            else:
                break
