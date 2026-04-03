#include "gtest/gtest.h"
#include "Solution.h"

TEST(LC3, ExampleTest) {
    Solution solution;
    std::string input = "abcabcbb";
    int expected = 3;  // "abc" is the longest substring without repeating characters
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

TEST(LC3, SingleCharacterString) {
    Solution solution;
    std::string input = "aaaaaa";
    int expected = 1;  // Only one unique character
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

TEST(LC3, AllUniqueCharacters) {
    Solution solution;
    std::string input = "abcdef";
    int expected = 6;  // All characters are unique
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

TEST(LC3, MixedDuplicates) {
    Solution solution;
    std::string input = "pwwkew";
    int expected = 3;  // "wke" is the longest substring
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

TEST(LC3, EmptyString) {
    Solution solution;
    std::string input = "";
    int expected = 0;  // No characters in the string
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

TEST(LC3, LongStringWithRepeatingPattern) {
    Solution solution;
    std::string input = "abababababababab";
    int expected = 2;  // "ab" is the longest substring without repeating characters
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

TEST(LC3, StringWithSpaces) {
    Solution solution;
    std::string input = "a b c d e";
    int expected = 3;  // "a b c" is the longest substring without repeating characters
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

TEST(LC3, StringLC) {
    Solution solution;
    std::string input = "aab";
    int expected = 2;  
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

TEST(LC3, StringLC1) {
    Solution solution;
    std::string input = "dvdf";
    int expected = 3;  
    EXPECT_EQ(solution.lengthOfLongestSubstring(input), expected);
}

