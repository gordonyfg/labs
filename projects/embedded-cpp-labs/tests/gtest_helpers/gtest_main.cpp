#include <gtest/gtest.h>

int main(int argc, char** argv) {
    // Initialize Google Test with command-line arguments
    ::testing::InitGoogleTest(&argc, argv);
    
    // Run all tests and return the results
    return RUN_ALL_TESTS();
}
