#include <iostream>

struct ListNode {
    int val;
    ListNode *next;
    ListNode(int x) : val(x), next(nullptr) {}
};

int main() {
    // Dynamic allocation (heap)
    ListNode *node1 = new ListNode(1);
    std::cout << "Value of node1: " << node1->val << std::endl; // Output: 1

    // Stack allocation
    ListNode node2(2);
    std::cout << "Value of node2: " << node2.val << std::endl; // Output: 2

    // Clean up dynamically allocated memory
    delete node1;

    return 0;
}