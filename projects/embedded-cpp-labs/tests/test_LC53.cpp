#include "gtest/gtest.h"
#include "Solution.h"

TEST(LC53, ExampleTest) {
    Solution solution;
    std::vector<int> input = {-2, 1, -3, 4, -1, 2, 1, -5, 4};
    int expected = 6;  // Subarray [4, -1, 2, 1] has the largest sum
    EXPECT_EQ(solution.maxSubArray(input), expected);
}

TEST(LC53, AllNegativeNumbers) {
    Solution solution;
    std::vector<int> input = {-8, -3, -6, -2, -5, -4};
    int expected = -2;  // Subarray [-2] has the largest sum
    EXPECT_EQ(solution.maxSubArray(input), expected);
}

TEST(LC53, SingleElementPositive) {
    Solution solution;
    std::vector<int> input = {5};
    int expected = 5;  // Single element array, sum is the element itself
    EXPECT_EQ(solution.maxSubArray(input), expected);
}

TEST(LC53, SingleElementNegative) {
    Solution solution;
    std::vector<int> input = {-5};
    int expected = -5;  // Single element array, sum is the element itself
    EXPECT_EQ(solution.maxSubArray(input), expected);
}

TEST(LC53, MixedPositiveAndNegative) {
    Solution solution;
    std::vector<int> input = {1, 2, -1, 2, -3, 4, -1};
    int expected = 5;  // Subarray [1, 2, -1, 2, -3, 4] gives sum 5
    EXPECT_EQ(solution.maxSubArray(input), expected);
}

TEST(LC53, AllPositiveNumbers) {
    Solution solution;
    std::vector<int> input = {1, 2, 3, 4, 5};
    int expected = 15;  // Entire array has the largest sum
    EXPECT_EQ(solution.maxSubArray(input), expected);
}