import unittest
from algorithms import bubble_sort, binary_search

class TestAlgorithms(unittest.TestCase):
    """
    Unit tests for bubble_sort and binary_search functions.
    """

    def test_bubble_sort(self):
        """
        Tests the bubble_sort function with various cases.
        """
        # Case 1: Unsorted list
        arr1 = [64, 34, 25, 12, 22, 11, 90]
        bubble_sort(arr1)
        self.assertEqual(arr1, [11, 12, 22, 25, 34, 64, 90])

        # Case 2: Already sorted list
        arr2 = [1, 2, 3, 4, 5]
        bubble_sort(arr2)
        self.assertEqual(arr2, [1, 2, 3, 4, 5])

        # Case 3: Empty list
        arr3 = []
        bubble_sort(arr3)
        self.assertEqual(arr3, [])

        # Case 4: Single element list
        arr4 = [1]
        bubble_sort(arr4)
        self.assertEqual(arr4, [1])

        # Case 5: List with duplicates
        arr5 = [5, 1, 4, 2, 8, 1, 5]
        bubble_sort(arr5)
        self.assertEqual(arr5, [1, 1, 2, 4, 5, 5, 8])

    def test_binary_search(self):
        """
        Tests the binary_search function with various cases.
        """
        sorted_arr = [11, 12, 22, 25, 34, 64, 90]

        # Case 1: Target is in the list
        self.assertEqual(binary_search(sorted_arr, 22), 2)
        self.assertEqual(binary_search(sorted_arr, 11), 0)
        self.assertEqual(binary_search(sorted_arr, 90), 6)

        # Case 2: Target is not in the list
        self.assertEqual(binary_search(sorted_arr, 100), -1)
        self.assertEqual(binary_search(sorted_arr, 5), -1)

        # Case 3: Empty list
        self.assertEqual(binary_search([], 10), -1)

        # Case 4: Single element list (found)
        self.assertEqual(binary_search([10], 10), 0)

        # Case 5: Single element list (not found)
        self.assertEqual(binary_search([10], 5), -1)

if __name__ == "__main__":
    unittest.main()
