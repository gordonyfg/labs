from algorithms import bubble_sort, binary_search
from data_processor import say_hello



def example_sort_search():
    """
    Demonstrates the functionality of bubble sort and binary search.
    """
    # Sample unsorted list
    data = [64, 34, 25, 12, 22, 11, 90]
    print(f"Original list: {data}")

    # Sorting the list
    bubble_sort(data)
    print(f"Sorted list: {data}")

    # Searching for an element
    target = 22
    index = binary_search(data, target)
    if index != -1:
        print(f"Element {target} found at index {index}.")
    else:
        print(f"Element {target} not found in the list.")


def example_data_processing():
    """
    Demonstrates the functionality of the data_processor module.
    """
    say_hello()



def main():
    """
    Entry point to showcase functionality.
    """
    example_sort_search()
    example_data_processing()



if __name__ == "__main__":
    main()