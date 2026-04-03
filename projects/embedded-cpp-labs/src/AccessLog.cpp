#include <iostream>
using namespace std;

const int maxSize = 5;
int accessLog[maxSize];
int amtEntries = 0;

void addEntry(int entry) {
    accessLog[amtEntries % maxSize] = entry;
    amtEntries++;
}

void printEntries() {
    cout << "Access Log Entries:" << endl;
    for (int i = 0; i < min(maxSize, amtEntries); i++) {
        cout << "Entry of index " << i << " : " << accessLog[i] << '\n';
    }
}

int main() {
    // Add entries to the log
    for(int i=1; i<=5;i++){
        addEntry(i);
    }
    
    // Print entries
    cout << "Initial state:\n";
    printEntries();

    // Add more entries to test circular behavior
    addEntry(6);
    addEntry(7);
    
    // Print entries again
    cout << "state after more entries\n";
    printEntries();

    return 0;
}