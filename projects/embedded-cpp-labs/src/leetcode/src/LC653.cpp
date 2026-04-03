#include "Solution.h"

void Solution::inorderTraversal(TreeNode *root, vector<int>& listInordertraversal)
{
    if (root == nullptr) {
        return;
    }
    
    // First traverse left subtree
    inorderTraversal(root->left, listInordertraversal);
    
    // Then add current node's value
    listInordertraversal.push_back(root->val);
    
    // Finally traverse right subtree
    inorderTraversal(root->right, listInordertraversal);
}

bool Solution::findTarget(TreeNode *root, int k)
{
    Solution solution;
    if (!root) return false;
    
    vector<int> listInordertraversal;
    inorderTraversal(root, listInordertraversal);
    
    // std::cout << "List contents: ";
    // for (const auto& num : listInordertraversal) {
    //     std::cout << num << " ";
    // }
    // std::cout << std::endl;
    
    return !twoSumSorted(listInordertraversal, k).empty();
}

// int main()
// {
//     Solution solution;

//     // Create a larger valid BST for testing
//     TreeNode *root = new TreeNode(8);
    
//     // Left subtree
//     root->left = new TreeNode(4);
//     root->left->left = new TreeNode(2);
//     root->left->right = new TreeNode(6);
//     root->left->left->left = new TreeNode(1);
//     root->left->left->right = new TreeNode(3);
//     root->left->right->left = new TreeNode(5);
//     root->left->right->right = new TreeNode(7);
    
//     // Right subtree
//     root->right = new TreeNode(12);
//     root->right->left = new TreeNode(10);
//     root->right->right = new TreeNode(14);
//     root->right->left->left = new TreeNode(9);
//     root->right->left->right = new TreeNode(11);
//     root->right->right->left = new TreeNode(13);
//     root->right->right->right = new TreeNode(15);

//     int target = 20;  // Try finding pairs that sum to 20
//     bool result = solution.findTarget(root, target);
//     std::cout << "Result: " << (result ? "true" : "false") << std::endl;

//     // Clean up memory
//     // TODO: Implement proper tree deletion to prevent memory leaks
//     return 0;
// }