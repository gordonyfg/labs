#ifndef LEETCODE_SOLUTION_H
#define LEETCODE_SOLUTION_H

#include <vector>
#include <iostream>
#include<unordered_map>
#include<unordered_set>
#include<algorithm>
#include <numeric>
using namespace std;

//  * Definition for a binary tree node.
struct TreeNode {
    int val;
    TreeNode *left;
    TreeNode *right;
    TreeNode() : val(0), left(nullptr), right(nullptr) {}
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    TreeNode(int x, TreeNode *left, TreeNode *right) : val(x), left(left), right(right) {}
};

class Solution {
public:
    std::vector<int> twoSum(std::vector<int>& numbers, int target);
    std::vector<int> twoSumSorted(std::vector<int>& numbers, int target);
    bool findTarget(TreeNode *root, int k);
    void inorderTraversal(TreeNode *root, vector<int>& listInordertraversal);
    int lengthOfLongestSubstring(string s);
    int maxSubArray(vector<int> &nums);
};

#endif // LEETCODE_SOLUTION_H
