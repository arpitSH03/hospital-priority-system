"""
Custom FIFO Queue Implementation Using Singly Linked List.

Designed for the Hospital Emergency and Patient Priority Management System.
Used to manage the available doctors queue in strict First-In, First-Out (FIFO)
order, ensuring fair rotation when assigning doctors to incoming emergency patients.
"""

from typing import Any, List, Optional
from dsa.linked_list import LinkedList


class Queue:
    """
    A FIFO (First-In, First-Out) Queue backed by a singly linked list.
    
    Items are enqueued at the tail and dequeued from the head,
    yielding O(1) time complexity for both operations.
    """

    def __init__(self) -> None:
        """
        Initializes an empty FIFO Queue.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        self._list: LinkedList = LinkedList()

    def is_empty(self) -> bool:
        """
        Checks whether the queue is empty.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            bool: True if queue has no items, False otherwise.
        """
        return self._list.is_empty()

    def size(self) -> int:
        """
        Returns the number of elements currently in the queue.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            int: The element count.
        """
        return self._list.size()

    def enqueue(self, item: Any) -> None:
        """
        Adds an item to the back (tail) of the queue.
        
        Time Complexity: O(1)
        Space Complexity: O(1) auxiliary space.
        
        Args:
            item: The element to add (e.g. a Doctor object or doctor ID).
        """
        self._list.append(item)

    def dequeue(self) -> Optional[Any]:
        """
        Removes and returns the front item of the queue.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            Optional[Any]: The front item, or None if the queue is empty.
        """
        return self._list.remove_first()

    def peek(self) -> Optional[Any]:
        """
        Returns the front item of the queue without removing it.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            Optional[Any]: The front item, or None if the queue is empty.
        """
        if self._list.head is None:
            return None
        return self._list.head.data

    def to_list(self) -> List[Any]:
        """
        Returns a Python list of queue items from front to back.
        
        Time Complexity: O(n) where n is the number of items.
        Space Complexity: O(n) to construct the output list.
        
        Returns:
            List[Any]: Items in FIFO order.
        """
        return self._list.to_list()

    def remove(self, item: Any) -> bool:
        """
        Removes a specific item from the queue if present.
        
        Time Complexity: O(n) where n is the number of items.
        Space Complexity: O(1) auxiliary space.
        
        Args:
            item: Item to remove.
            
        Returns:
            bool: True if removed, False otherwise.
        """
        return self._list.remove(item)

    def contains(self, item: Any) -> bool:
        """
        Checks whether an item is currently present in the queue.
        
        Time Complexity: O(n)
        Space Complexity: O(1)
        
        Args:
            item: Item to check.
            
        Returns:
            bool: True if present, False otherwise.
        """
        return self._list.find(lambda x: x == item) is not None

    def __iter__(self):
        """
        Allows iteration over items from front to back.
        
        Time Complexity: O(n)
        Space Complexity: O(1)
        """
        return iter(self._list)
