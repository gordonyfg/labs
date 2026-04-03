# Embedded-Cpp
Embedded-Cpp is a comprehensive repository showcasing my revision and projects in embedded systems programming using C and C++. This repository includes code snippets, scripts, tutorials, and full-scale projects covering various aspects of embedded development.

Example
1. AccessLog
2. LRU
3. Merge_SLL
4. heap_stack

Leetcode
1. LC167 Two Sum II - Input Array Is Sorted
2. LC653 Two Sum IV - Input is a BST

2024-12-23 Folder Structure Explain
To keep project structured and maintainable as i work through 
LeetCode questions and integrate GTest with CI:
```
.
├── .github/
│   └── workflows/
│       └── cmake-gtest.yml      # GitHub Actions CI configuration
├── .vscode/
│   └── (VS Code settings files)
├── cmake/                      # CMake configuration files (optional, reusable modules)
├── gtest/                      # GTest setup and tests
│   ├── src/
│   │   └── main.cpp            # Main file for GTest runner
│   ├── tests/
│   │   ├── test_LC167.cpp      # Unit tests for LC167
│   │   └── (other tests here)
│   └── CMakeLists.txt          # CMake configuration for GTest setup
├── leetcode/
│   ├── src/
│   │   ├── LC167.cpp           # Solution for LC167
│   │   ├── LC168.cpp           # (Other solutions)
│   │   └── ...
│   ├── include/                # Shared headers for solutions, if needed
│   ├── README.md
│   └── CMakeLists.txt          # CMake configuration for LeetCode solutions
├── CMakeLists.txt              # Top-level CMake configuration
└── README.md                   # Project documentation
```