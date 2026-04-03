"""
This module contains implementations of binary search and bubble sort algorithms.
"""

def bubble_sort(arr):
    """
    Sorts a list in-place using the bubble sort algorithm.

    Args:
        arr (list): The list of elements to be sorted.
    """
    n = len(arr)
    # Traverse through all array elements
    for i in range(n):
        # Last i elements are already in place
        for j in range(0, n - i - 1):
            # Traverse the array from 0 to n-i-1
            # Swap if the element found is greater than the next element
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]

def binary_search(arr, target):
    """
    Finds the index of a target value within a sorted list using binary search.

    Args:
        arr (list): A sorted list of elements.
        target: The value to search for.

    Returns:
        int: The index of the target if found, otherwise -1.
    """
    low = 0
    high = len(arr) - 1

    while low <= high:
        mid = (low + high) // 2
        guess = arr[mid]

        if guess == target:
            return mid
        if guess > target:
            high = mid - 1
        else:
            low = mid + 1

    return -1
