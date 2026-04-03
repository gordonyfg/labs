cmake_minimum_required(VERSION 3.16)

project(embedded_cpp)

# Set the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Add main leetcode solutions library
file(GLOB LEETCODE_SOURCES 
    "src/*.cpp"
    "src/leetcode/src/*.cpp"
)

add_library(leetcode_solutions STATIC
    ${LEETCODE_SOURCES}
)

# Include directories for leetcode solutions
target_include_directories(leetcode_solutions PUBLIC
    ${CMAKE_SOURCE_DIR}/src
)

# Find and link GoogleTest
find_package(GTest REQUIRED)

# Add tests executable
file(GLOB TEST_SOURCES
    "tests/gtest_helpers/*.cpp"
    "tests/*.cpp"
)

add_executable(tests
    ${TEST_SOURCES}
)

# Include directories for tests
target_include_directories(tests PRIVATE
    ${CMAKE_SOURCE_DIR}/tests
    ${CMAKE_SOURCE_DIR}/src
    ${CMAKE_SOURCE_DIR}/src/leetcode/src
)

# Link libraries for tests
target_link_libraries(tests PRIVATE
    GTest::gtest
    GTest::gtest_main
    leetcode_solutions
)

# Enable testing
enable_testing()
add_test(NAME AllTests COMMAND tests)
