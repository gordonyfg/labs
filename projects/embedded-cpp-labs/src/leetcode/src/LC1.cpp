#include "Solution.h"

// class Solution {
// public:
    vector<int> Solution::twoSum(vector<int>& nums, int target) {
        unordered_map<int, int> valueMap;
        for(int i = 0; i < nums.size(); i++){
            int complement = target - nums[i];
            if(valueMap.find(complement) != valueMap.end()){
                return {valueMap[complement], i};
            }
            valueMap[nums[i]] = i;
        }
        return {};
    }
// };