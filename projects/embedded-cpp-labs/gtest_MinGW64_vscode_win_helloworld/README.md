
---

# GTest Hello World Example on Windows (MSYS2 + MinGW-w64 + vcpkg)

This repository demonstrates how to set up a simple Google Test unit test in a Windows environment using:

- MSYS2
- MinGW-w64
- vcpkg package manager
- CMake
- Visual Studio Code (optional, but recommended)

## 1. Prerequisites

1. **MSYS2**  
   - [Install MSYS2](https://www.msys2.org/).  
   - Update packages with `pacman`.  
   - Ensure you add the following directory to your Windows `PATH`:
     ```
     C:\msys64\mingw64\bin
     ```
   - In an **MSYS2 terminal** (MingW64 shell), install these packages:
     ```bash
     pacman -S --needed git base-devel mingw-w64-x86_64-toolchain mingw-w64-x86_64-clang mingw-w64-x86_64-cmake
     ```
   - Create a symlink so that `make` is recognized as `mingw32-make`:
     ```bash
     cd /mingw64/bin
     ln -s mingw32-make.exe make.exe
     ```

2. **Visual Studio Code** (optional but handy)  
   - Install [VS Code](https://code.visualstudio.com/).  
   - Install extensions for C/C++ development (e.g., [C/C++](https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools), [CMake Tools](https://marketplace.visualstudio.com/items?itemName=ms-vscode.cmake-tools), etc.).

---

## 2. Install vcpkg in MSYS2 (MingW64 Terminal)

1. Open the **MSYS2 MingW64** variant of the console:
   ```bash
   cd /mingw64/bin
   git clone https://github.com/microsoft/vcpkg.git
   cd vcpkg
   ```
2. Bootstrap vcpkg:
   ```bash
   ./bootstrap-vcpkg.bat
   ```
3. Set environment variables for the default triplet (so that future vcpkg commands default to `x64-mingw-dynamic`):
   ```bash
   export VCPKG_DEFAULT_TRIPLET=x64-mingw-dynamic
   export VCPKG_DEFAULT_HOST_TRIPLET=x64-mingw-dynamic
   ```
4. Install **Google Test**:
   ```bash
   ./vcpkg install gtest
   ```
5. Integrate vcpkg into your environment (optional):
   ```bash
   ./vcpkg integrate install
   ```
6. Verify installation:
   ```bash
   ./vcpkg list
   ```
   You should see something like:
   ```
   gtest:x64-mingw-dynamic         1.15.2  Google Testing and Mocking Framework
   ...
   ```

---

## 3. Create the Project Folder

Create a new folder (e.g., `gtest_minimal`) with this structure:

```
gtest_minimal/
├── CMakeLists.txt
├── src/
│   └── main.cpp
└── tests/
    └── test_helloworld.cpp
```

Below are sample contents for each file.

### CMakeLists.txt

```cmake
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
```

### src/main.cpp

```cpp
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
```

### tests/test_helloworld.cpp

```cpp
#include <gtest/gtest.h>

// Simple function to test
int add(int a, int b) {
    return a + b;
}

// Basic test for the add function
TEST(HelloWorldTest, TestAdd) {
    EXPECT_EQ(add(2, 2), 4);
    EXPECT_EQ(add(-1, 1), 0);
}

TEST(HelloWorldTest, AnotherTest) {
    EXPECT_TRUE(true);
}
```

---

## 4. Build the Project

1. Open an **MSYS2 MingW64** terminal and navigate to the project folder:
   ```bash
   cd /path/to/gtest_minimal
   mkdir build && cd build
   ```
2. Run CMake, telling it to use MinGW Makefiles, the vcpkg toolchain file, and your desired triplet:
   ```bash
   cmake -G "MinGW Makefiles" \
     -DCMAKE_TOOLCHAIN_FILE="C:/msys64/mingw64/bin/vcpkg/scripts/buildsystems/vcpkg.cmake" \
     -DVCPKG_TARGET_TRIPLET=x64-mingw-dynamic \
     ..
   ```
   > **Note**  
   > Adjust the path to `vcpkg.cmake` if it differs in your setup.

3. Build with:
   ```bash
   cmake --build .
   ```
   This should produce two executables in your `build` directory:
   - `helloworld`
   - `tests`

---

## 5. Run the Tests

Inside the `build` directory, run:

```bash
./tests
```

You should see output similar to:

```
[==========] Running 2 tests from 1 test suite.
[----------] Global test environment set-up.
[ RUN      ] HelloWorldTest.TestAdd
[       OK ] HelloWorldTest.TestAdd (0 ms)
[ RUN      ] HelloWorldTest.AnotherTest
[       OK ] HelloWorldTest.AnotherTest (0 ms)
[----------] Global test environment tear-down
[==========] 2 tests from 1 test suite ran. (1 ms total)
[  PASSED  ] 2 tests.
```

If the tests pass, you have successfully integrated **Google Test** in a minimal MSYS2 + MinGW + vcpkg environment!

---

## 6. Optional: Visual Studio Code Integration

- Install the **CMake Tools** and **C/C++** extensions.  
- Open your project folder in VS Code.  
- Configure the project using the **CMake Tools** extension (it will detect your CMakeLists.txt).  
- Set your preferred compiler (MinGW-w64) and the toolchain file in the extension settings.  
- Build and run your tests directly from VS Code.

---

## Summary

1. **Set up MSYS2** with the MinGW-w64 toolchain and symlink `make`.  
2. **Install vcpkg** under MSYS2’s MingW64 environment.  
3. **Install GTest** with the correct triplet (e.g., `x64-mingw-dynamic`).  
4. **Create a CMake project**, referencing the vcpkg toolchain file.  
5. **Build** the project using MinGW Makefiles, then **run** your tests.

That’s it! You now have a simple working example of **Google Test** under Windows using MSYS2, MinGW-w64, vcpkg, and CMake. Happy coding!