2024_11_10
AccessLog.cpp
    shows how to implement an access log which will overwrite the oldest entries when we run out of space. This type of system is helpful in embedded systems where we want to ensure that the memory taken up by the logs does not take over the system or get fragmented.

2024_11_17
LRU.cpp
    Data structures play a vital role in organizing and managing data efficiently in embedded software applications. 

    Linked Lists
        Singly Linked Lists: Used for sequential data storage, where each node points to the next.
            Ideal for operations needing forward-only traversal, like a printer queue.

        Variations:
            Doubly Linked Lists: Allow movement both ways by having nodes point to predecessor and successor.

            Circular Linked Lists: Tail node points back to the head, forming a loop.
        
        Complexity:
            Memory: O(n), scales with the number of nodes.
            Time: O(1) for end insertions (as long as we have pointers to both the head and tail of the list); O(n) for insertions/removals in the middle.

    Unordered Maps
        Implemented using hash tables, which support key-value associations.

        Complexity:
        Constant-time complexity O(1) for insertions, deletions, and searches.

        Prioritizes quick access over element order, suitable for applications requiring fast key-based retrieval.

    Note:
        Dereference the iterator by *. e.g. *it

2024_11_18
Structs and Pointers

