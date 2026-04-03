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

# Create a test executable
add_executable(tests tests/test_helloworld.cpp)

# Link GTest to the test executable
target_link_libraries(tests PRIVATE GTest::gtest GTest::gtest_main)

# Enable CTest
enable_testing()
add_test(NAME MyHelloWorldTest COMMAND tests)
