"""
Custom Hash Map Implementation with Separate Chaining and Dynamic Resizing.

Designed for the Hospital Emergency and Patient Priority Management System.
Provides O(1) average-time lookups, insertions, updates, and deletions for
mapping patient_id -> Patient and doctor_id -> Doctor.

Handles hash collisions via bucket chaining and automatically resizes (doubles capacity)
when the load factor exceeds 0.75.
"""

from typing import Any, List, Optional, Tuple


class HashMap:
    """
    A separate-chaining Hash Map.
    
    Attributes:
        _capacity (int): The current number of allocated buckets.
        _load_factor_threshold (float): Threshold ratio (size / capacity) that triggers resizing.
        _size (int): The current count of stored key-value pairs.
        _buckets (List[List[List[Any]]]): Array of buckets, each holding [key, value] pairs.
    """

    def __init__(self, initial_capacity: int = 16, load_factor_threshold: float = 0.75) -> None:
        """
        Initializes an empty HashMap with given capacity and load factor threshold.
        
        Time Complexity: O(capacity) to initialize bucket array.
        Space Complexity: O(capacity) to allocate bucket references.
        
        Args:
            initial_capacity: Starting number of hash buckets (default: 16).
            load_factor_threshold: Maximum load factor before triggering resize (default: 0.75).
        """
        if initial_capacity < 1:
            raise ValueError("Initial capacity must be at least 1.")

        self._capacity: int = initial_capacity
        self._load_factor_threshold: float = load_factor_threshold
        self._size: int = 0
        self._buckets: List[List[List[Any]]] = [[] for _ in range(self._capacity)]

    def _hash(self, key: Any) -> int:
        """
        Computes the bucket index for a given key.
        
        Time Complexity: O(1) for typical numeric/string keys.
        Space Complexity: O(1)
        
        Args:
            key: Hashable object.
            
        Returns:
            int: Bucket index within [0, self._capacity - 1].
        """
        return hash(key) % self._capacity

    def size(self) -> int:
        """
        Returns the number of key-value pairs stored in the hash map.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            int: Total stored entries.
        """
        return self._size

    def is_empty(self) -> bool:
        """
        Checks whether the hash map contains zero entries.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            bool: True if empty, False otherwise.
        """
        return self._size == 0

    def contains(self, key: Any) -> bool:
        """
        Determines whether the given key exists in the hash map.
        
        Time Complexity: O(1) average, O(n) worst-case (all keys collide in one bucket).
        Space Complexity: O(1)
        
        Args:
            key: Key to test for existence.
            
        Returns:
            bool: True if key is present, False otherwise.
        """
        bucket_idx = self._hash(key)
        bucket = self._buckets[bucket_idx]
        for pair in bucket:
            if pair[0] == key:
                return True
        return False

    def get(self, key: Any, default: Optional[Any] = None) -> Optional[Any]:
        """
        Retrieves the value associated with key, or default if key is not found.
        
        Time Complexity: O(1) average, O(n) worst-case.
        Space Complexity: O(1)
        
        Args:
            key: The lookup key.
            default: Value returned if key is missing (default: None).
            
        Returns:
            Optional[Any]: Stored value or default.
        """
        bucket_idx = self._hash(key)
        bucket = self._buckets[bucket_idx]
        for pair in bucket:
            if pair[0] == key:
                return pair[1]
        return default

    def put(self, key: Any, value: Any) -> None:
        """
        Inserts or updates a key-value pair in the hash map.
        
        If the key already exists, its value is updated in place.
        If the key is new, it is appended to the appropriate bucket chain.
        If the load factor exceeds 0.75 after insertion, capacity is doubled.
        
        Time Complexity: O(1) average, O(n) worst-case or when resize is triggered.
                         Amortized O(1).
        Space Complexity: O(1) auxiliary space (O(n) during resize).
        
        Args:
            key: The key to insert or update.
            value: The associated value.
        """
        bucket_idx = self._hash(key)
        bucket = self._buckets[bucket_idx]

        # Update existing key if present
        for pair in bucket:
            if pair[0] == key:
                pair[1] = value
                return

        # Insert new key-value pair
        bucket.append([key, value])
        self._size += 1

        # Check load factor for dynamic resizing
        if (self._size / self._capacity) > self._load_factor_threshold:
            self._resize(self._capacity * 2)

    def remove(self, key: Any) -> Any:
        """
        Removes the key-value pair associated with key and returns the value.
        
        Time Complexity: O(1) average, O(n) worst-case.
        Space Complexity: O(1)
        
        Args:
            key: The key to remove.
            
        Returns:
            Any: The value that was removed.
            
        Raises:
            KeyError: If the key is not found.
        """
        bucket_idx = self._hash(key)
        bucket = self._buckets[bucket_idx]

        for i, pair in enumerate(bucket):
            if pair[0] == key:
                val = pair[1]
                del bucket[i]
                self._size -= 1
                return val

        raise KeyError(f"Key '{key}' not found in HashMap.")

    def _resize(self, new_capacity: int) -> None:
        """
        Rehashes all current entries into a new bucket array of size new_capacity.
        
        Time Complexity: O(n + capacity) where n is the number of entries.
        Space Complexity: O(new_capacity) for the new bucket array.
        
        Args:
            new_capacity: The new number of buckets.
        """
        old_buckets = self._buckets
        self._capacity = new_capacity
        self._buckets = [[] for _ in range(self._capacity)]
        self._size = 0  # Re-populated via put()

        for bucket in old_buckets:
            for pair in bucket:
                self.put(pair[0], pair[1])

    def keys(self) -> List[Any]:
        """
        Returns a list of all keys currently stored.
        
        Time Complexity: O(n + capacity)
        Space Complexity: O(n) for the output list.
        
        Returns:
            List[Any]: All stored keys.
        """
        result = []
        for bucket in self._buckets:
            for pair in bucket:
                result.append(pair[0])
        return result

    def values(self) -> List[Any]:
        """
        Returns a list of all values currently stored.
        
        Time Complexity: O(n + capacity)
        Space Complexity: O(n) for the output list.
        
        Returns:
            List[Any]: All stored values.
        """
        result = []
        for bucket in self._buckets:
            for pair in bucket:
                result.append(pair[1])
        return result

    def items(self) -> List[Tuple[Any, Any]]:
        """
        Returns a list of (key, value) tuples for all stored entries.
        
        Time Complexity: O(n + capacity)
        Space Complexity: O(n) for the output list.
        
        Returns:
            List[Tuple[Any, Any]]: All (key, value) pairs.
        """
        result = []
        for bucket in self._buckets:
            for pair in bucket:
                result.append((pair[0], pair[1]))
        return result

    # Dunder methods for idiomatic Python access: map[k] = v, map[k], del map[k], k in map
    def __getitem__(self, key: Any) -> Any:
        val = self.get(key)
        if val is None and not self.contains(key):
            raise KeyError(f"Key '{key}' not found in HashMap.")
        return val

    def __setitem__(self, key: Any, value: Any) -> None:
        self.put(key, value)

    def __delitem__(self, key: Any) -> None:
        self.remove(key)

    def __contains__(self, key: Any) -> bool:
        return self.contains(key)

    def __len__(self) -> int:
        return self._size
