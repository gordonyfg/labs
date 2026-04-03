#!/bin/bash

# Set variables
BUILD_DIR="build"

# Clean up the build directory if it exists
if [ -d "$BUILD_DIR" ]; then
    echo "Cleaning up the build directory..."
    rm -rf "$BUILD_DIR"
fi

# Create a new build directory
mkdir "$BUILD_DIR"
cd "$BUILD_DIR" || exit

# Configure the project with CMake
echo "Configuring the project..."
cmake .. -DCMAKE_BUILD_TYPE=Release
if [ $? -ne 0 ]; then
    echo "CMake configuration failed!"
    exit 1
fi

# Build the project
echo "Building the project..."
cmake --build .
if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

# Run tests using CTest
echo "Running tests..."
ctest --output-on-failure
if [ $? -ne 0 ]; then
    echo "Tests failed!"
    exit 1
fi

# Optional: Run the test binary directly
echo "Running test binary..."
if [ -f tests ]; then
    ./tests
fi

echo "Build and tests completed successfully!"
