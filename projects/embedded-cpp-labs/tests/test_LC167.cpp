#include "gtest/gtest.h"
#include "Solution.h"

TEST(LC167, ExampleTest) {
    Solution solution;
    std::vector<int> input = {2, 7, 11, 15};
    int target = 9;
    std::vector<int> expected = {1, 2};
    EXPECT_EQ(solution.twoSumSorted(input, target), expected);
}

TEST(LC167, EdgeCaseTest) {
    Solution solution;
    std::vector<int> input = {1, 2};
    int target = 3;
    std::vector<int> expected = {1, 2};
    EXPECT_EQ(solution.twoSumSorted(input, target), expected);
}