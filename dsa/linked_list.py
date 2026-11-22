"""
Custom Singly Linked List Implementation.

Designed for the Hospital Emergency and Patient Priority Management System.
Used to maintain each patient's linear treatment history (status changes,
treatment notes, doctor assignments, and timestamps) and discharged patient records.
"""

from typing import Any, Callable, List, Optional


class Node:
    """
    A single node in the singly linked list.
    
    Attributes:
        data (Any): Payload stored in the node (e.g. treatment record, patient log).
        next (Optional[Node]): Pointer to the next node in the list.
    """

    def __init__(self, data: Any) -> None:
        """
        Initializes a new node with data and null next pointer.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        self.data: Any = data
        self.next: Optional["Node"] = None


class LinkedList:
    """
    A singly linked list with head and tail pointers.
    
    Attributes:
        head (Optional[Node]): Pointer to the first node.
        tail (Optional[Node]): Pointer to the last node.
        _size (int): Current number of nodes in the list.
    """

    def __init__(self) -> None:
        """
        Initializes an empty linked list.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        self.head: Optional[Node] = None
        self.tail: Optional[Node] = None
        self._size: int = 0

    def is_empty(self) -> bool:
        """
        Checks if the linked list is empty.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            bool: True if empty, False otherwise.
        """
        return self._size == 0

    def size(self) -> int:
        """
        Returns the number of elements in the linked list.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            int: The node count.
        """
        return self._size

    def append(self, data: Any) -> None:
        """
        Inserts a new element at the end of the list (tail).
        
        Using the maintained tail pointer, insertion is O(1).
        
        Time Complexity: O(1)
        Space Complexity: O(1) auxiliary space (O(1) new node created).
        
        Args:
            data: The payload to append.
        """
        new_node = Node(data)
        if self.head is None:
            self.head = new_node
            self.tail = new_node
        else:
            self.tail.next = new_node
            self.tail = new_node
        self._size += 1

    def prepend(self, data: Any) -> None:
        """
        Inserts a new element at the front of the list (head).
        
        Time Complexity: O(1)
        Space Complexity: O(1) auxiliary space.
        
        Args:
            data: The payload to prepend.
        """
        new_node = Node(data)
        if self.head is None:
            self.head = new_node
            self.tail = new_node
        else:
            new_node.next = self.head
            self.head = new_node
        self._size += 1

    def remove_first(self) -> Optional[Any]:
        """
        Removes and returns the data from the front (head) of the list.
        
        Time Complexity: O(1)
        Space Complexity: O(1)
        
        Returns:
            Optional[Any]: Data from the removed head node, or None if list is empty.
        """
        if self.head is None:
            return None

        removed_data = self.head.data
        self.head = self.head.next
        self._size -= 1

        if self.head is None:
            self.tail = None

        return removed_data

    def remove(self, target_or_predicate: Any) -> bool:
        """
        Removes the first node whose data equals target_or_predicate or
        satisfies target_or_predicate(data) if a callable is provided.
        
        Time Complexity: O(n) where n is the number of nodes in the list.
        Space Complexity: O(1) auxiliary space.
        
        Args:
            target_or_predicate: Value to match, or a predicate function f(data) -> bool.
            
        Returns:
            bool: True if an element was found and removed, False otherwise.
        """
        if self.head is None:
            return False

        def matches(data: Any) -> bool:
            if callable(target_or_predicate):
                return bool(target_or_predicate(data))
            return data == target_or_predicate

        # Case 1: Head node matches
        if matches(self.head.data):
            self.remove_first()
            return True

        # Case 2: Node is in the middle or at the tail
        current = self.head
        while current.next is not None:
            if matches(current.next.data):
                # Remove current.next
                node_to_remove = current.next
                current.next = node_to_remove.next
                
                # If removed node was the tail, update tail to current
                if node_to_remove == self.tail:
                    self.tail = current
                    
                self._size -= 1
                return True
            current = current.next

        return False

    def find(self, target_or_predicate: Any) -> Optional[Any]:
        """
        Searches for the first element matching target_or_predicate.
        
        Time Complexity: O(n) where n is the number of nodes.
        Space Complexity: O(1) auxiliary space.
        
        Args:
            target_or_predicate: Value to find or predicate function f(data) -> bool.
            
        Returns:
            Optional[Any]: The node data if found, or None if not found.
        """
        def matches(data: Any) -> bool:
            if callable(target_or_predicate):
                return bool(target_or_predicate(data))
            return data == target_or_predicate

        current = self.head
        while current is not None:
            if matches(current.data):
                return current.data
            current = current.next

        return None

    def to_list(self) -> List[Any]:
        """
        Traverses the linked list from head to tail and returns a Python list of data.
        
        Time Complexity: O(n) where n is the number of nodes.
        Space Complexity: O(n) to construct and return the output list.
        
        Returns:
            List[Any]: Elements in list order.
        """
        result: List[Any] = []
        current = self.head
        while current is not None:
            result.append(current.data)
            current = current.next
        return result

    def __iter__(self):
        """
        Generator to iterate over node data in the list.
        
        Time Complexity: O(n)
        Space Complexity: O(1)
        """
        current = self.head
        while current is not None:
            yield current.data
            current = current.next
