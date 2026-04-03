#include <gtest/gtest.h>

// A simple function to test
int add(int a, int b) {
    return a + b;
}

// Basic test for the add function
TEST(HelloWorldTest, TestAdd) {
    EXPECT_EQ(add(2, 2), 4);
    EXPECT_EQ(add(-1, 1), 0);
}

// Another trivial test
TEST(HelloWorldTest, AnotherTest) {
    EXPECT_TRUE(true);
}
