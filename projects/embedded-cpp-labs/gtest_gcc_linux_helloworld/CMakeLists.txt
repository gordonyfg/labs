cmake_minimum_required(VERSION 3.10)
project(GTestHelloWorld CXX)

# 1) Option A: Hard-code the vcpkg toolchain file here
#set(CMAKE_TOOLCHAIN_FILE "C:/msys64/mingw64/bin/vcpkg/scripts/buildsystems/vcpkg.cmake" CACHE STRING "" FORCE)

# 2) Option B: Omit the above set(...) and rely on -DCMAKE_TOOLCHAIN_FILE=... in the command line

# Set the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Create an executable from main.cpp
add_executable(helloworld src/main.cpp)

# ---[ Google Test ]---
find_package(GTest CONFIG REQUIRED)

# Create a test executable with a different name
add_executable(run_tests tests/test_helloworld.cpp)

# Link GTest to the test executable
target_link_libraries(run_tests PRIVATE GTest::gtest GTest::gtest_main)

# Enable CTest
enable_testing()
add_test(NAME MyHelloWorldTest COMMAND run_tests)

add_custom_target(tests_run ALL
    COMMAND run_tests
    DEPENDS run_tests
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)