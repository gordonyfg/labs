#include <gtest/gtest.h>
#include "leetcode/src/Solution.h"

class LC653Test : public ::testing::Test {
protected:
    Solution solution;
    
    // Helper function to create a BST from a vector
    TreeNode* createBST(const vector<int>& values, int start, int end) {
        if (start > end) return nullptr;
        
        int mid = (start + end) / 2;
        TreeNode* root = new TreeNode(values[mid]);
        
        root->left = createBST(values, start, mid - 1);
        root->right = createBST(values, mid + 1, end);
        
        return root;
    }
    
    // Helper function to delete the BST
    void deleteBST(TreeNode* root) {
        if (!root) return;
        deleteBST(root->left);
        deleteBST(root->right);
        delete root;
    }
};

TEST_F(LC653Test, Example1) {
    vector<int> values = {5, 3, 6, 2, 4, 7};
    TreeNode* root = createBST(values, 0, values.size() - 1);
    
    EXPECT_TRUE(solution.findTarget(root, 9));  // 2 + 7 = 9
    
    deleteBST(root);
}

TEST_F(LC653Test, Example2) {
    vector<int> values = {5, 3, 6, 2, 4, 7};
    TreeNode* root = createBST(values, 0, values.size() - 1);
    
    EXPECT_FALSE(solution.findTarget(root, 28));  // No pair sums to 28
    
    deleteBST(root);
}

TEST_F(LC653Test, EmptyTree) {
    EXPECT_FALSE(solution.findTarget(nullptr, 0));
}

TEST_F(LC653Test, SingleNode) {
    TreeNode* root = new TreeNode(1);
    EXPECT_FALSE(solution.findTarget(root, 2));
    delete root;
}

TEST_F(LC653Test, LargerTree) {
    vector<int> values = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    TreeNode* root = createBST(values, 0, values.size() - 1);
    
    EXPECT_TRUE(solution.findTarget(root, 15));  // 5 + 10 = 15
    EXPECT_TRUE(solution.findTarget(root, 7));   // 3 + 4 = 7
    EXPECT_FALSE(solution.findTarget(root, 20)); // No pair sums to 20
    
    deleteBST(root);
}
