#include "Solution.h"

// class Solution {
// public:
 int Solution::lengthOfLongestSubstring(string s) {
    unordered_set<char> charSet;  // To store unique characters in the window
    int left = 0;                 // Left pointer of the sliding window
    int maxLength = 0;            // Maximum length of substring

    for (int right = 0; right < s.length(); ++right) {
        // If duplicate character found, shrink the window from the left
        while (charSet.find(s[right]) != charSet.end()) {
            charSet.erase(s[left]);
            left++;
        }

        // Add the current character to the set
        charSet.insert(s[right]);

        // Update maxLength
        maxLength = max(maxLength, right - left + 1);
    }

    return maxLength;
}
// };