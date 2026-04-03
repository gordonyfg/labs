//two-pointer technique
//Advantages: 
//Reduces complexity from O(n²) (nested loops) to O(n) for many problems.
//Simple to implement.

/* 167. Two Sum II - Input Array Is Sorted
Medium
Topics
Companies
Given a 1-indexed array of integers numbers that is already sorted in non-decreasing order, find two numbers such that they add up to a specific target number. Let these two numbers be numbers[index1] and numbers[index2] where 1 <= index1 < index2 <= numbers.length.

Return the indices of the two numbers, index1 and index2, added by one as an integer array [index1, index2] of length 2.

The tests are generated such that there is exactly one solution. You may not use the same element twice.

Your solution must use only constant extra space.

 

Example 1:

Input: numbers = [2,7,11,15], target = 9
Output: [1,2]
Explanation: The sum of 2 and 7 is 9. Therefore, index1 = 1, index2 = 2. We return [1, 2].
Example 2:

Input: numbers = [2,3,4], target = 6
Output: [1,3]
Explanation: The sum of 2 and 4 is 6. Therefore index1 = 1, index2 = 3. We return [1, 3].
Example 3:

Input: numbers = [-1,0], target = -1
Output: [1,2]
Explanation: The sum of -1 and 0 is -1. Therefore index1 = 1, index2 = 2. We return [1, 2].
 

Constraints:

2 <= numbers.length <= 3 * 104
-1000 <= numbers[i] <= 1000
numbers is sorted in non-decreasing order.
-1000 <= target <= 1000
The tests are generated such that there is exactly one solution. */

#include "Solution.h"

// class Solution {
// public:
    vector<int> Solution::twoSumSorted(vector<int>& numbers, int target) {
        int left = 0;
        int right = numbers.size() - 1;
        
        // Ensure pointers don't go out of bounds
        while (left < right) {
            int sum = numbers[left] + numbers[right];
            
            if (sum == target) {
                return {left + 1, right + 1}; // Found pair
            } else if (sum < target) {
                ++left; // Increase sum
            } else {
                --right; // Decrease sum
            }
        }
        
        return {}; // Return empty if no valid pair is found
    }
// };

// //Local Testing
// // Function to print the results
// void printResult(const vector<int>& result) {
//     cout << "[";
//     for (size_t i = 0; i < result.size(); ++i) {
//         cout << result[i];
//         if (i != result.size() - 1) cout << ", ";
//     }
//     cout << "]" << endl;
// }

// // Main function for testing
// int main() {
//     Solution solution;

//     // Test cases
//     vector<vector<int>> testNumbers = {
//         {2, 7, 11, 15},
//         {1, 2, 3, 4, 4, 9, 56, 90},
//         {1, 3, 5, 6},
//         {-10, -5, -2, -1, 0, 3, 8}
//     };

//     vector<int> testTargets = {9, 8, 9, -9};

//     vector<vector<int>> expectedResults = {
//         {1, 2},
//         {4, 5},
//         {2, 4},
//         {1, 6}
//     };

//     // Run test cases
//     for (size_t i = 0; i < testNumbers.size(); ++i) {
//         vector<int> result = solution.twoSum(testNumbers[i], testTargets[i]);
//         cout << "Test Case " << i + 1 << ": ";
//         cout << "Input numbers = ";
//         printResult(testNumbers[i]);
//         cout << "Target = " << testTargets[i] << endl;
//         cout << "Expected = ";
//         printResult(expectedResults[i]);
//         cout << "Output = ";
//         printResult(result);
//         cout << (result == expectedResults[i] ? "✅ Passed" : "❌ Failed") << endl;
//         cout << "---------------------------" << endl;
//     }

//     return 0;
// }

/* Test Result:

Test Case 1: Input numbers = [2, 7, 11, 15]
Target = 9
Expected = [1, 2]
Output = [1, 2]
✅ Passed
Test Case 2: Input numbers = [1, 2, 3, 4, 4, 9, 56, 90]
Target = 8
Expected = [4, 5]
Output = [4, 5]
✅ Passed
Test Case 3: Input numbers = [1, 3, 5, 6]
Target = 9 */
