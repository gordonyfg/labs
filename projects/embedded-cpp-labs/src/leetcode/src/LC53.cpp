#include "Solution.h"


    // int Solution::maxSubArray(vector<int>& nums) {
    //     vector<int> numsArray;  // To store unique characters in the window
    //     int left = 0;                 // Left pointer of the sliding window
    //     int maxSum = 0;            // Maximum length of substring
    //     int currentSum = 0;
    //     numsArray.push_back(nums[left]);
    //     currentSum = nums[left];

    //     for (int right = 1; right < nums.size(); ++right) {
    //         numsArray.push_back(nums[right]);
    //         auto result = std::reduce(numsArray.begin(), numsArray.end());
    //         cout << "result: " << result << endl;
    //         if (result > currentSum) {
    //             currentSum = result;
    //         }else{
    //             numsArray.pop_back();
    //             left = right+1;
    //         }
    //         if (std::reduce(numsArray.begin()+1, numsArray.end())>currentSum){
    //             numsArray.erase(numsArray.begin());
    //             left++;
    //         }
    //         maxSum = max(maxSum, currentSum);
    //     }
    //     return maxSum;
    // }


    int Solution::maxSubArray(vector<int> &arr) {
    int res = arr[0];
    int maxEnding = arr[0];

    for (int i = 1; i < arr.size(); i++) {
      
        // Find the maximum sum ending at index i by either extending 
        // the maximum sum subarray ending at index i - 1 or by
        // starting a new subarray from index i
        maxEnding = max(maxEnding + arr[i], arr[i]);
      
        // Update res if maximum subarray sum ending at index i > res
        res = max(res, maxEnding);
    }
    return res;
    }