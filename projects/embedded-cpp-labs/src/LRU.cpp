#include <iostream>
#include <list>
#include <unordered_map>

using namespace std;

struct LRU { //Least Recently Used Cache(LRU)
    const int maxCapacity = 1000;
    int currentCount = 0;
    unordered_map<int, int> valueMap;
    unordered_map<int,  list<int>::iterator> iteratorMap;
    list<int> keys;

    bool getEntry(int key, int &value) {
        if(valueMap.find(key) != valueMap.end()){ //found
            keys.erase(iteratorMap[key]); // Remove the key from the keys list using its stored iterator to avoid searching.
            keys.push_front(key); //update order
            iteratorMap[key] = keys.begin(); //save the pointer.
            value = valueMap[key]; //save the value.
            return true;
        }
        else{
            return false;
        }
    }

    void insertPair(int key, int value) {
        if(valueMap.find(key) != valueMap.end()){ //key is in valueMap
            keys.erase(iteratorMap[key]); //Get the iterator with key "key". Then erase the element in keys with the iterator(pointer).
            keys.push_front(key); //put key to the front of list keys.
            iteratorMap[key] = keys.begin(); //update iteratorMap with key "key" and value "pointer of the first element in list keys" 
            valueMap[key] = value; //update valueMap with key "key", value "value". 
            // valueMap does not maintain the order of keys; it only provides fast access to the values associated with the keys.
            //list keys actually hold the actual existence of key and the order of key. 
            //iteratorMap hold the pointer of individual key. Benefit: avoid searching in list keys.
        }
        else{ // Key is not in valueMap; handle maxCapacity and implement LRU eviction policy if necessary.
            if(currentCount >= maxCapacity){
                int LRUKey = keys.back(); //get least(last) used key
                valueMap.erase(LRUKey); //erase value with LRUKey
                iteratorMap.erase(LRUKey); //erase iterator with LRUKey
                keys.pop_back(); //Remove last element
                currentCount--;
            }
            valueMap[key]= value; //add new key value pair to valueMap
            keys.push_front(key); //add key to the front of keys
            iteratorMap[key] = keys.begin(); //add iterator of the key to the Map
            currentCount++;
        }
    }
};