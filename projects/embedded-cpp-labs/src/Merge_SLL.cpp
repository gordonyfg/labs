#include <iostream>

/* Implement the function mergeTwoLists that takes two pointers, 
l1 and l2, each pointing to the head of a sorted linked list. 
Merge these two linked lists in ascending order by node value. 
The function should return a pointer to the head of the merged and sorted linked list. 
The merging should be done in place with constant memory complexity. */

struct ListNode {
    int val;
    ListNode *next;
    ListNode(int x) : val(x), next(nullptr) {}
};

ListNode* mergeTwoLists(ListNode* l1, ListNode* l2) {
    // TODO: implement this function as per the instructions

    // Create a dummy node to serve as the start of the merged list
    ListNode dummy(0);
    ListNode* current = &dummy;

    // While both lists are non-empty, compare the values at the heads of the lists
    // Append the smaller value to the merged list
    while (l1 != nullptr && l2 != nullptr) {
        if (l1->val < l2->val) {
            current->next = l1;
            l1 = l1->next;
        } else {
            current->next = l2;
            l2 = l2->next;
        }
        current = current->next;
    }

    // At this point, at least one of the lists is empty.
    // Append the remaining elements of the non-empty list to the merged list.
    if (l1 != nullptr) {
        current->next = l1;
    } else {
        current->next = l2;
    }

    // The merged list starts at dummy.next
    return dummy.next;
}

// Helper function to print the list (for testing purposes)
void printList(ListNode* node) {
    while (node != nullptr) {
        std::cout << node->val;
        if(node->next != nullptr){
            std::cout << " -> ";
        }
        node = node->next;
    }
}

int main() {
    // Example usage:
    // List 1: 1 -> 3 -> 5
    ListNode* l1 = new ListNode(1);
    l1->next = new ListNode(3);
    l1->next->next = new ListNode(5);

    // List 2: 2 -> 4 -> 6
    ListNode* l2 = new ListNode(2);
    l2->next = new ListNode(4);
    l2->next->next = new ListNode(6);

    ListNode* mergedList = mergeTwoLists(l1, l2);

    // Expected outcome : 1 -> 2 -> 3 -> 4 -> 5 -> 6
    printList(mergedList);

    return 0;
}