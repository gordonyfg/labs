#include "gtest/gtest.h"
#include "Solution.h"

TEST(LC1, ExampleTest) {
    Solution solution;
    std::vector<int> input = {2, 7, 11, 15};
    int target = 9;
    std::vector<int> expected = {0, 1};  // Indices start from 0 for twoSum
    EXPECT_EQ(solution.twoSum(input, target), expected);
}

TEST(LC1, EdgeCaseTest_SmallArray) {
    Solution solution;
    std::vector<int> input = {3, 3};
    int target = 6;
    std::vector<int> expected = {0, 1};
    EXPECT_EQ(solution.twoSum(input, target), expected);
}

TEST(LC1, EdgeCaseTest_NegativeNumbers) {
    Solution solution;
    std::vector<int> input = {-1, -2, -3, -4, -5};
    int target = -8;
    std::vector<int> expected = {2, 4};
    EXPECT_EQ(solution.twoSum(input, target), expected);
}

TEST(LC1, EdgeCaseTest_NoSolution) {
    Solution solution;
    std::vector<int> input = {1, 2, 3, 4, 5};
    int target = 10;  // No two numbers sum to 10
    std::vector<int> expected = {};  // Assuming twoSum returns an empty vector
    EXPECT_EQ(solution.twoSum(input, target), expected);
}
